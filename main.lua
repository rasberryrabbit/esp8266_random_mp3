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
  { [4] = gpio.LOW, delay=25000 },
  { [4] = gpio.HIGH, delay=10000 }
})

pplay = gpio.pulse.build( {
  { [4] = gpio.LOW, delay=70000 },
  { [4] = gpio.HIGH, delay=25000 }
})

plreset = gpio.pulse.build( {
  { [4] = gpio.LOW, delay=25000 },
  { [4] = gpio.HIGH, delay=10000, loop=1, count=2 }
})

function stoppulse()
  plreset:cancel(function(pos, steps, offset, now) end)  
  pulser:cancel(function(pos, steps, offset, now) end)  
  pplay:cancel(function(pos, steps, offset, now) end)
end

function ReadConfig()
  fd=file.open("config.txt",'r')
  if fd~=nil then
    vol=fd:readline()
    fd:close()
    return tonumber(vol)
  else
    return 11
  end
end

dfvol=ReadConfig()
print(dfvol)

tick=0

worker=tmr.create()
worker:register(1000, tmr.ALARM_AUTO , function(t)
  currtime=rtctime.get()
  if workid==0 or currtime-dplast>=172800 then
    dfres=0
    lasttime=rtctime.get()
    dplast=lasttime
    dofile("cc.lua").ply(0x0c,0x00,0x00)
    stoppulse()
    plreset:start(function() end)
    print("[0]reset player")
    workid=1
  elseif workid==1 then
    if currtime-lasttime>=10 or dfres==1 or gpio.read(7)==1 then
      dfres=0
      lasttime=rtctime.get()
      dofile("cc.lua").ply(0x06,0x00,dfvol)
      print("[1]set volume")
      workid=2
    end
  elseif workid==2 then
    if currtime-lasttime>=10 or dfres==1 or gpio.read(7)==1 then
      dfres=0
      dfpmedia=0
      lasttime=rtctime.get()
      dofile("cc.lua").ply(0x4e,0x00,0x01)
      print("[2]query tracks")
      workid=3
    end
  elseif workid==3 then
    if currtime-lasttime>=10 or dfres==1 then
      print("[3]Start player")
      intv=10
      print(intv)
      stoppulse()
      pulser:start(function() end)
      workid=7
    end
  -- repeat
  elseif workid==7 then
    if currtime-lasttime>=1 or dfres==1 then
      dofile("cc.lua").ply(0x11,0x00,0x00)
      print("[7]disable repeat")
      workid=5
    end
  -- wait playback finished
  elseif workid==8 then
    if gpio.read(7)==1 then
      workid=7
      intv=node.random(30,180)
      lasttime=rtctime.get()
      print("[8]finished")
      print(intv)
    end
  elseif workid==5 then
    tick=tick+1
    currtime=rtctime.get()
    if currtime-lasttime>=intv then
      stoppulse()
      pulser:start(function() end)
      if gpio.read(7)==1 then
        stoppulse()
        pplay:start(function() end)
        tick=0
        if dfperror==4 or dfperror==8 then
          dfres=1
          intv=1
          workid=0
        else
          print("[5]play")
          if maxsnd>0 then
            print("MP3 Files "..string.format("%d",maxsnd))
            local rfile=node.random(1,maxsnd)
            print("rfile "..string.format("%d",rfile))
            -- folder nn, file nnn
            dofile("cc.lua").ply(0x0F,0x01,rfile)
            workid=8
          elseif maxsnd==0 then
            -- query files
            dfres=1
            intv=1
            workid=2
          end
        end
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