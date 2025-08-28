from machine import Pin
from machine import UART
from machine import Timer
import neopixel
import micropython
import time, random, struct, configreader

micropython.alloc_emergency_exception_buf(100)

random.seed(time.ticks_ms())

is_vcc_gnd=1
if is_vcc_gnd:
    # turn off neopixel, VCC GND
    npin=Pin(23, Pin.OUT)
    led=neopixel.NeoPixel(npin,1)
    led[0]=(0,0,0)
    led.write()
    
    # user input , 0 = active, VCC GND
    userpin=Pin(24, Pin.IN, Pin.PULL_UP)
else:
    userpin=None
    led=None

# turn off led, VCC GND
lpin=Pin(25, Pin.OUT)
lpin.value(0)


# init uart
ucmd=0
udata=0
ubuf=bytearray(64)
dfrecv=1

uart1=UART(1, 9600)

def uart_event(uart):
    if uart.any()>=10:
        micropython.schedule(uart_process,uart)
        
def uart_process(data):
    global dfrecv
    if dfrecv==1:
        nread=uart1.readinto(ubuf)
        print(ubuf[:10].hex())
    dfrecv=1

uart1.init(baudrate=9600,tx=Pin(4),rx=Pin(5),timeout=1000)
uart1.irq(handler=uart_event,trigger=UART.IRQ_RXIDLE,hard=True)

# init dfp power
dfon=Pin(7, Pin.OUT)
dfon.value(0)
time.sleep(1)

# dfp busy pin
stby=Pin(6, Pin.IN)

# dfp functions
def dfp_write_data(cmd, dataL=0, dataH=0, result=False):
    global dfrecv
    if uart1.any()>0:
        uart1.readinto(ubuf)
    checksum=0xffff-(0xff+0x06+cmd+0x00+dataH+dataL)+1
    cksum=checksum.to_bytes(2,'big')
    uart1.write(b'\x7E')        # Start
    uart1.write(b'\xFF')        # Firmware version
    uart1.write(b'\x06')        # Command length
    uart1.write(bytes([cmd]))   # Command word
    uart1.write(b'\x00')        # Feedback flag
    uart1.write(bytes([dataH])) # DataH
    uart1.write(bytes([dataL])) # DataL
    uart1.write(cksum)          # checksum High
    uart1.write(b'\xEF')        # Stop
    if result:
        dfrecv=0

    # give device some time
    if cmd == 0x09:                        # set_media
      time.sleep(0.200)
    elif cmd == 0x0C:                      # reset
      time.sleep(1.000)
    elif cmd in [0x47,0x48,0x49,0x4E]:     # query files
      time.sleep(0.500)
    else:
      time.sleep(0.100)            # other commands
      
    # read from dfplayer
    stime = time.ticks_ms()
    while dfrecv==0:
        time.sleep(0.01)
        if time.ticks_diff(time.ticks_ms(), stime)>=300:
            if uart1.any()==0:
                return 0
    nread=uart1.readinto(ubuf)
    ucmd=ubuf[3]
    udata=struct.unpack('>h',ubuf[5:7])[0]
    return udata

# init dfp
dfon.value(1)
time.sleep(1)

config=configreader.ConfigReader()
config.read('config.txt')

try:
    vol=int(config.option['vol'])
except:
    vol=8
    pass

timeval = 0
lastplay=0

if led:
    led[0]=(0,0,50)
    led.write()
else:
    lpin.value(1)
try:
    # volume
    dfp_write_data(cmd=0x06,dataL=vol)
    # file count
    nfiles=dfp_write_data(cmd=0x4e,dataL=1,result=True)
except Exception as e:
    nfiles=0
    print(e)
if led:
    led[0]=(0,0,0)
    led.write()
else:
    lpin.value(0)

def get_delay():
    return random.randrange(180-45)+45

print("MP3 Files : %d" % nfiles)
#while not stby.value():
#    time.sleep(0.01)
print(stby.value())
# get volume
vol=dfp_write_data(cmd=0x43,result=True)
print("volume %d" %vol)
lastdelay=10
print("delay %d" % lastdelay)

# timer
tim=Timer()

lastplay=0
timeval=0

def time_func(t):
    global vol, timeval, lastdelay, lastplay
    timeval+=1
    if lastdelay<=timeval:
        try:
            if stby.value():
                if led:
                    led[0]=(50,0,0)
                    led.write()
                else:
                    lpin.value(1)
                # volume
                dfp_write_data(cmd=0x06,dataL=vol)
                # prevent repeat
                dfp_write_data(cmd=0x19,dataL=0x01)
                # get new MP3 track
                nplay=lastplay
                while lastplay==nplay:
                    nplay=random.randrange(nfiles)+1
                lastplay=nplay
                # play MP3 track
                dfp_write_data(cmd=0x14,dataL=nplay & 0xff,dataH=0x10+int(nplay/256))
                if led:
                    led[0]=(0,0,0)
                    led.write()
                else:
                    lpin.value(0)
                print("play %d" % nplay)
        except KeyboardInterrupt:
            tim.deinit()
        except Exception as e:
            print(e)
        # reset timer
        timeval=0
        lastdelay=get_delay()
        print("lastdelay %d" % lastdelay)
    else:
        # blink every 10 seconds
        if timeval % 10==0:
            if led:
                led[0]=(0,50,0)
                led.write()
            else:
                lpin.value(1)
            time.sleep(0.02)
            if led:
                led[0]=(0,0,0)
                led.write()
            else:
                lpin.value(0)
    if userpin and not userpin.value():
        tim.deinit()
   
tim.init(mode=Timer.PERIODIC, period=1000, callback=time_func)
