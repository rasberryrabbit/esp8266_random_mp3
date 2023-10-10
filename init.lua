maxsnd=0
maxfolder=0
_G.dfres=0

sply = softuart.setup(9600, 6, 5) -- TX d6, RX d5, for DFPlayer
sply:on("data",10, function(data) -- 10 bytes returns from DFPlayer
  local rs=""
  if string.byte(data,4)==0x4E then
    maxsnd=string.byte(data,7)
  end
  if string.byte(data,4)==0x4F then
    maxfolder=string.byte(data,7)
  end
  _G.dfres=1
  for i=1,#data do
    rs=rs .. string.format("%02x",string.byte(data,i)) .. " "
  end
  print(rs)
end)

local scnt=0
local mcnt=0

gpio.mode(7,gpio.INPUT) -- Busy d7

starttmr=tmr.create()
starttmr:register(1000, tmr.ALARM_AUTO, function(t)
  tm = rtctime.epoch2cal(rtctime.get())
  if tm["year"]~=1970 or mcnt>15 then
    starttmr:unregister()
    if mcnt>15 or wifi.getmode()==wifi.NULLMODE then
      rtctime.set(1609459200, 0)
      print("Set 1609459200")
    end
    print(rtctime.get())
    if file.exists("main.lua") then
      dofile("main.lua")
    end
  end;
  mcnt=mcnt+1
  print(mcnt)
end)

function synctime()
  sntp.sync()
end

--[[ delaytmr=tmr.create()
delaytmr:register(1000, tmr.ALARM_AUTO, function()
  scnt=scnt+1
  print(scnt)
  if scnt>15 then
    delaytmr:unregister()
    if file.exists("apconn.lua") then
      dofile("apconn.lua")
    end

    pcall(synctime)
    
    starttmr:start()
    print("timer: starttmr")
  end
end)

delaytmr:start() ]]--
wifi.setmode(wifi.NULLMODE)

starttmr:start()

print("timer: delaytmr")
