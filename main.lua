lasttime=rtctime.get()
intv=node.random(45,180)
_G.lastid=0

print("main")

-- cc.lua reset uart to 9600
-- play volume 20
dofile("cc.lua").ply(0x06,0x00,0x14)
print(gpio.read(7))

worker=tmr.create()
worker:register(1000, tmr.ALARM_AUTO , function(t)
    currtime=rtctime.get()
    if currtime-lasttime>=intv then
      if gpio.read(7)==1 then
        lasttime=currtime
        print("play")
        intv=node.random(45,180)
        local rfile=node.random(1,11)
        -- folder nn, file nnn
        dofile("cc.lua").ply(0x03,0x01,rfile)
        print(intv)
      end
    end
  end)
worker:start()
print("timer: worker")