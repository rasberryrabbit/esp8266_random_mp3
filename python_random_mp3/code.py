import board
import busio
import digitalio
import time
import neopixel
import random, struct, configreader
import asyncio

#from DFPlayer import DFPlayer
from adafruit_ticks import ticks_ms, ticks_add, ticks_less

# init random
random.seed(ticks_ms())

# user break pin BUTTON
userpin=digitalio.DigitalInOut(board.BUTTON)
userpin.switch_to_input(pull=digitalio.Pull.UP)

# dfp power pin = GP7
dfon=digitalio.DigitalInOut(board.GP7)
dfon.switch_to_output(value=True,drive_mode=digitalio.DriveMode.PUSH_PULL)
time.sleep(1)

# standby pin GP6
stby=digitalio.DigitalInOut(board.GP6)
stby.switch_to_input(pull=None)

# init neopixel
led = neopixel.NeoPixel(board.NEOPIXEL, 1)

# uart tx = GP4, rx = GP5
uart1 = busio.UART(board.GP4, board.GP5, baudrate=9600)

ucmd=0
udata=0

async def uart_reader(uart):
    global ucmd, udata, led
    while True:
        if uart.in_waiting>=10:
            buf=uart.read(10)
            if buf:
                if buf[0]==0x7e:
                    ucmd=buf[3]
                    udata=struct.unpack('>h',buf[5:7])[0]
                    print(hex(ucmd), hex(udata))
                else:
                    led[0]=(0,0,50)
                    time.sleep(0.02)
                    led[0]=(0,0,0)
        await asyncio.sleep(0.01)

def dfp_write_data(cmd, dataL=0, dataH=0):
    global ucmd
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
    uart1.reset_input_buffer()
    ucmd=0

    # give device some time
    if cmd == 0x09:                        # set_media
      time.sleep(0.200)
    elif cmd == 0x0C:                      # reset
      time.sleep(1.000)
    elif cmd in [0x47,0x48,0x49,0x4E]:     # query files
      time.sleep(0.500)
    else:
      time.sleep(0.100)            # other commands


def dfp_read_data():
    outtime = ticks_add(ticks_ms(), 300)
    while uart1.in_waiting<10:
        time.sleep(0.01)
        if not ticks_less(ticks_ms(), outtime):
            if uart1.in_waiting==0:
                return None
    buf=uart1.read(10)
    if buf:
        return struct.unpack('>h',buf[5:7])[0]
    else:
        return None

# turn on dfplayer
dfon.value=True
time.sleep(1)

config=configreader.ConfigReader()
config.read('config.txt')

try:
    vol=int(config.option['vol'])
except:
    vol=8
    pass

global nfiles
# init dfplayer
  
def get_delay():
    return random.randrange(180-45)+45


# timer loop
async def main_loop():
    global led, stby, userpin, vol
    deadline = ticks_add(ticks_ms(), 1000)
    timeval = 0
    lastplay=0

    led[0]=(0,0,50)
    try:
        # volume
        dfp_write_data(cmd=0x06,dataL=vol)
        dfp_read_data()
        # file count
        dfp_write_data(cmd=0x4e,dataL=1)
        nfiles=dfp_read_data()
    except Exception as e:
        nfiles=0
        print(e)
    led[0]=(0,0,0)    

    print("MP3 Files : %d" % nfiles)
    while not stby.value:
        await asyncio.sleep(0.01)
    print(stby.value)
    # get volume
    dfp_write_data(cmd=0x43)
    vol=dfp_read_data()
    print("volume %d" %vol)
    lastdelay=get_delay()
    print("delay %d" % lastdelay)

    while True:
        # interval proc
        if not ticks_less(ticks_ms(), deadline):
            timeval+=1
            if lastdelay<=timeval:
                try:
                    if stby.value:
                        led[0]=(50,0,0)
                        # volume
                        dfp_write_data(cmd=0x06,dataL=vol)
                        dfp_read_data()
                        # prevent repeat
                        dfp_write_data(cmd=0x19,dataL=0x01)
                        dfp_read_data()
                        # get new MP3 track
                        nplay=lastplay
                        while lastplay==nplay:
                            nplay=random.randrange(nfiles)+1
                        lastplay=nplay
                        # play MP3 track
                        dfp_write_data(cmd=0x14,dataL=nplay & 0xff,dataH=0x10+int(nplay/256))
                        led[0]=(0,0,0)
                        dfp_read_data()
                        print("play %d" % nplay)
                except Exception as e:
                    print(e)
                # reset timer
                timeval=0
                lastdelay=get_delay()
                print("lastdelay %d" % lastdelay)
            else:
                # blink every 10 seconds
                if timeval % 10==0:
                    led[0]=(0,50,0)
                    time.sleep(0.02)
                    led[0]=(0,0,0)
            #dfp_read_dummy()
            # 1000ms
            deadline=ticks_add(ticks_ms(), 1000)                
        # user stop
        if not userpin.value:
            break
        await asyncio.sleep(0.01)

async def main():
    t1=asyncio.create_task(uart_reader(uart1))
    t2=asyncio.create_task(main_loop())
    await asyncio.gather(t1, t2)
    
asyncio.run(main())

