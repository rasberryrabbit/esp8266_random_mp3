lasttime=rtctime.get()
intv=node.random(45,180)
_G.lastid=0
gpio.mode(4, gpio.OUTPUT)
gpio.write(4, gpio.HIGH)
workid=0

print("main")

print(gpio.read(7))

-- cc.lua reset uart to 9600

pulser = gpio.pulse.build( {
  { [4] = gpio.LOW, delay=50000 },
  { [4] = gpio.HIGH, delay=50000 }
})

pplay = gpio.pulse.build( {
  { [4] = gpio.LOW, delay=200000 },
  { [4] = gpio.HIGH, delay=50000 }
})


tick=0

worker=tmr.create()
worker:register(1000, tmr.ALARM_AUTO , function(t)
  currtime=rtctime.get()
  if workid==0 then
    _G.dfres=0
    lasttime=rtctime.get()
    dofile("cc.lua").ply(0x0c,0x00,0x00)
    print("reset player")
    workid=1
  elseif workid==1 then
    if currtime-lasttime>=10 or _G.dfres==1 or gpio.read(7)==1 then
      _G.dfres=0
      lasttime=rtctime.get()
      dofile("cc.lua").ply(0x06,0x00,0x14)
      print("set volume")
      workid=2
    end
  elseif workid==2 then
    if currtime-lasttime>=10 or _G.dfres==1 or gpio.read(7)==1 then
      _G.dfres=0
      lasttime=rtctime.get()
      dofile("cc.lua").ply(0x4e,0x00,0x01)
      print("query tracks")
      workid=3
    end
  elseif workid==3 then
    if currtime-lasttime>=10 or _G.dfres==1 then
      print("Start player")
      workid=5
    end
  elseif workid==5 then
    tick=tick+1
    currtime=rtctime.get()
    if currtime-lasttime>=intv then
      pplay:start(function() end)
      if gpio.read(7)==1 then
        tick=0
        lasttime=currtime
        print("play")
        intv=node.random(45,180)
        if maxsnd>0 then
          print("MP3 Files "..string.format("%d",maxsnd))
          local rfile=node.random(1,maxsnd)
          print("rfile "..string.format("%d",rfile))
          -- folder nn, file nnn
          dofile("cc.lua").ply(0x03,0x01,rfile)
        else
          -- query files
          _G.dfres=1
          workid=2
        end
        print(intv)
      elseif tick>120 then
        tick=0
        -- reset dfplayer
        workid=0
      end
    else
      --pulser:start(function() end)
    end
  end
end)
  
worker:start()
print("timer: worker")