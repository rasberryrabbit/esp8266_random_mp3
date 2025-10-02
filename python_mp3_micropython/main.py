from machine import Pin
from machine import UART
from machine import Timer
import neopixel
import micropython
import time, random, struct, configreader
import asyncio

micropython.alloc_emergency_exception_buf(100)

random.seed(time.ticks_us())

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
lpin.off()


# init uart
ucmd=0
udata=0
ubuf=bytearray(64)
nread=0


uartev=asyncio.Event()
uartev.set()

dfpreset=asyncio.Event()
dfpreset.clear()

mediaready=asyncio.Event()
mediaready.set()

nfiles=0

uart1=UART(1, 9600)

def uart_event(uart):
    global uartev, ubuf, nread
    if uart.any()>=10:
        nread=uart.readinto(ubuf)
        uartev.set()
        # dump data
        micropython.schedule(uart_process,nread)
        
def uart_process(data):
    global uartev, dfpreset, ubuf, mediaready, nfilesm, lastplayed
    iread=data
    # try to fix serial data alignment
    ipos=0
    while ipos<iread:
        for i in range(ipos,iread):
            if ubuf[i]==0x7e:
                ipos=i
                break
        ucmd=ubuf[ipos+3]
        udata=struct.unpack('>h',ubuf[ipos+5:ipos+7])[0]
        if ucmd==0x3f:
            mediaready.set()
            print("media type %d" %udata)
        elif ucmd==0x3d:
            print("track played %d" % udata)
        elif ucmd==0x3b:
            mediaready.clear()
            nfiles=0
        # error
        elif ucmd==0x40:
            if udata==0x03:
                if led:
                    led[0]=(50,50,0)
                    led.write()
                dfpreset.set()
                print("Serial Error")
            elif udata==0x04:
                if led:
                    led[0]=(0,50,50)
                    led.write()
                dfpreset.set()
                print("Checksum invalid")
            elif udata==0x08:
                if led:
                    led[0]=(0,0,50)
                    led.write()
                dfpreset.set()
                print("SDCard Read error")
        else:
            print(ubuf[ipos+3:ipos+7].hex())
        ipos+=10

uart1.init(baudrate=9600,tx=Pin(4),rx=Pin(5),timeout=1000)
uart1.irq(handler=uart_event,trigger=UART.IRQ_RXIDLE,hard=True)

# init dfp power
dfon=Pin(7, Pin.OUT)
dfon.off()

# dfp busy pin
stby=Pin(6, Pin.IN)

# dfp functions
def dfp_write_data(cmd, dataL=0, dataH=0, result=False):
    global uartev, ubuf, nread
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
    uartev.clear()

    # give device some time
    if cmd == 0x09:                        # set_media
      time.sleep(0.200)
    elif cmd == 0x0C:                      # reset
      time.sleep(1.000)
    elif cmd in [0x47,0x48,0x49,0x4E]:     # query files
      time.sleep(0.700)
    else:
      time.sleep(0.100)            # other commands
      
    # read from dfplayer
    stime = time.ticks_ms()
    while not uartev.is_set():
        time.sleep(0.01)
        if time.ticks_diff(time.ticks_ms(), stime)>=300:
            break
    # try to fix serial data alignment
    ipos=0
    for i in range(0,10):
        if ubuf[i]==0x7e:
            ipos=i
            break
    # cmd, data
    ucmd=ubuf[ipos+3]
    udata=struct.unpack('>h',ubuf[ipos+5:ipos+7])[0]
    return udata

# init dfp

config=configreader.ConfigReader()
config.read('config.txt')

try:
    vol=int(config.option['vol'])
except:
    vol=8
    pass

timeval = 0
lastdelay=0

def dfp_init():
    global lastdelay, vol
    dfon.off()
    time.sleep(1)
    dfon.on()
    time.sleep(1.5)
    if led:
        led[0]=(0,0,50)
        led.write()
    else:
        lpin.on()
    # volume
    dfp_write_data(cmd=0x06,dataL=vol)
    if led:
        led[0]=(0,0,0)
        led.write()
    else:
        lpin.off()
    #while not stby.value():
    #    time.sleep(0.01)
    print(stby.value())
    # get volume
    vol=dfp_write_data(cmd=0x43,result=True)
    print("volume %d" %vol)
    lastdelay=10
    print("delay %d" % lastdelay)


def get_delay():
    return random.randrange(120-45)+45


# timer
tim=Timer()

lastplay=0
timeval=0

def time_func(t):
    global vol, timeval, lastdelay, lastplay, mediaready, nfiles
    timeval+=1
    if lastdelay<=timeval:
        try:
            if nfiles and stby.value():
                if led:
                    led[0]=(50,0,0)
                    led.write()
                else:
                    lpin.on()
                # volume
                dfp_write_data(cmd=0x06,dataL=vol)
                # get new MP3 track
                nplay=lastplay
                while lastplay==nplay:
                    nplay=random.randrange(nfiles)+1
                lastplay=nplay
                # play MP3 track
                dfp_write_data(cmd=0x14,dataL=nplay & 0xff,dataH=0x10+int(nplay/256))
                # prevent repeat
                dfp_write_data(cmd=0x19,dataL=0x01)
                if led:
                    led[0]=(0,0,0)
                    led.write()
                else:
                    lpin.off()
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
                lpin.on()
            time.sleep(0.02)
            if led:
                led[0]=(0,0,0)
                led.write()
            else:
                lpin.off()
    if userpin and not userpin.value():
        tim.deinit()
    if mediaready.is_set():
        # file count
        nfiles=dfp_write_data(cmd=0x4e,dataL=1,result=True)
        if nfiles:
            mediaready.clear()
        print("MP3 Files : %d" % nfiles)
    # reset dfp
    if dfpreset.is_set():
        dfpreset.clear()
        dfp_init()
        
# start
dfp_init()
tim.init(mode=Timer.PERIODIC, period=1000, callback=time_func)
