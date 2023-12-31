lasttime=rtctime.get()
intv=node.random(45,180)
lastid=0
gpio.mode(4, gpio.OUTPUT)
gpio.write(4, gpio.HIGH)
workid=0
dplast=rtctime.get()

print("main")

print(gpio.read(7))

-- cc.lua reset uart to 9600

pulser = gpio.pulse.build( {
  { [4] = gpio.LOW, delay=50000 },
  { [4] = gpio.HIGH, delay=50000, loop=1, count=2 }
})

pplay = gpio.pulse.build( {
  { [4] = gpio.LOW, delay=100000 },
  { [4] = gpio.HIGH, delay=50000 }
})


tick=0

worker=tmr.create()
worker:register(1000, tmr.ALARM_AUTO , function(t)
  currtime=rtctime.get()
  if workid==0 or currtime-dplast>=259200 then
    dfres=0
    lasttime=rtctime.get()
    dplast=lasttime
    dofile("cc.lua").ply(0x0c,0x00,0x00)
    pulser:start(function() end)
    print("reset player")
    workid=1
  elseif workid==1 then
    if currtime-lasttime>=10 or dfres==1 or gpio.read(7)==1 then
      dfres=0
      lasttime=rtctime.get()
      dofile("cc.lua").ply(0x06,0x00,0x14)
      print("set volume")
      workid=2
    end
  elseif workid==2 then
    if currtime-lasttime>=10 or dfres==1 or gpio.read(7)==1 then
      dfres=0
      dfpmedia=0
      lasttime=rtctime.get()
      dofile("cc.lua").ply(0x4e,0x00,0x01)
      print("query tracks")
      workid=3
    end
  elseif workid==3 then
    if currtime-lasttime>=10 or dfres==1 then
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
        if dfperror==4 or dfperror==8 then
          dfres=1
          intv=1
          workid=0
        elseif maxsnd>0 then
          print("MP3 Files "..string.format("%d",maxsnd))
          local rfile=node.random(1,maxsnd)
          print("rfile "..string.format("%d",rfile))
          -- folder nn, file nnn
          dofile("cc.lua").ply(0x03,0x01,rfile)
        else
          -- query files
          dfres=1
          intv=1
          workid=2
        end
        print(intv)
      elseif tick>120 then
        tick=0
        -- reset dfplayer
        workid=0
      end
    else
      if dfpmedia==1 then
        dfres=1
        workid=2
        print("Plugin")
      end
      --pulser:start(function() end)
    end
  end
end)
  
worker:start()
print("timer: worker")