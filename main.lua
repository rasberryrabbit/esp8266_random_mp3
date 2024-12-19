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

tick=0
readyid=0

worker=tmr.create()
worker:register(1000, tmr.ALARM_AUTO , function(t)
  currtime=rtctime.get()
  if workid==0 or currtime-dplast>=172800 then
    dfres=0
    lasttime=rtctime.get()
    dplast=lasttime
    dofile("cc.lua").ply(0x0c,0x00,0x00)
    gpio.write(4, gpio.LOW)    
    stoppulse()
    plreset:start(function() end)
    workid=10
    print("[0]reset player")
  elseif workid==10 then
    gpio.write(4, gpio.HIGH)
    workid=12
    print("[10]Turn on Player")
  elseif workid==12 then
    workid=2
    print(gpio.read(7))
  elseif workid==2 then
    if currtime-lasttime>=10 or gpio.read(7)==1 then
      dfres=0
      dfpmedia=0
      lasttime=rtctime.get()
      dofile("cc.lua").ply(0x4e,0x00,0x01)
      workid=3
      print("[2]query tracks")
    end
  elseif workid==3 then
    if currtime-lasttime>=10 or dfres==1 or gpio.read(7)==1 then
      print("MP3 Files "..string.format("%d",maxsnd))
      intv=10
      print(intv)
      stoppulse()
      pulser:start(function() end)
      workid=7
      print("[3]Start player")
    end
  -- repeat
  elseif workid==7 then
    if currtime-lasttime>=1 or gpio.read(7)==1 then
      dfres=0
      dofile("cc.lua").ply(0x11,0x00,0x00)
      workid=1
      print("[7]disable repeat")
    end
  elseif workid==1 then
    if currtime-lasttime>=10 or gpio.read(7)==1 then
      dfres=0
      lasttime=rtctime.get()
      svol=string.format("0x%x",dfvol)
      dofile("cc.lua").ply(0x06,0x00,tonumber(dfvol))
      workid=5
      print("[1]set volume "..dfvol)
    end
  -- wait playback finished
  elseif workid==8 then
    if gpio.read(7)==1 then
      workid=7
      intv=node.random(50,120)
      lasttime=rtctime.get()
      print("[8]finished")
      print("Wait for "..intv)
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
          if maxsnd>0 then
            dfres=0
            local rfile=node.random(1,maxsnd)
            -- folder 1 = 0x10, file nnnn, 15 folders 3000+ files
            byte1 = string.format("0x%02x",0x10 + rfile / 256)
            byte2 = string.format("0x%02x",rfile % 256)
            dofile("cc.lua").ply(0x14,tonumber(byte1),tonumber(byte2))
            workid=8
            print("[5]play track "..string.format("%s %s",byte1,byte2))
          elseif maxsnd==0 then
            -- query files
            dfres=1
            intv=1
            workid=2
          end
        end
      end
    else
      if dfpmedia==1 and gpio.read(7)==1 then
        --dfres=1
        workid=2
        print("Plug in")
      end
      if tick % 5==0 then
        stoppulse()
        pulser:start(function() end)
      end
    end
  end
end)
  
worker:start()
print("timer: worker")