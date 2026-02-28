-- imv-sync.lua — imv Fenster folgt nvim Tab-Wechseln
-- Bei BufEnter auf Bild-Datei: imv öffnen oder vorhandenes Fenster updaten

local image_exts = { png=true, jpg=true, jpeg=true, gif=true, webp=true, bmp=true, tiff=true, avif=true, ico=true }

local imv_job = nil
local imv_pid = nil

local function is_image(file)
  local ext = file:match("%.(%w+)$")
  return ext and image_exts[ext:lower()]
end

local function imv_alive()
  return imv_job ~= nil and vim.fn.jobwait({ imv_job }, 0)[1] == -1
end

local function show(filepath)
  if imv_alive() then
    vim.fn.system({ "imv-msg", tostring(imv_pid), "close all" })
    vim.fn.system({ "imv-msg", tostring(imv_pid), "open", filepath })
  else
    imv_job = vim.fn.jobstart({ "imv", filepath }, {
      detach = true,
      on_exit = function() imv_job = nil; imv_pid = nil end,
    })
    imv_pid = vim.fn.jobpid(imv_job)
  end
end

vim.api.nvim_create_autocmd("BufEnter", {
  desc = "imv-sync: Bild in imv anzeigen",
  callback = function(ev)
    local file = vim.api.nvim_buf_get_name(ev.buf)
    if file ~= "" and is_image(file) and vim.fn.filereadable(file) == 1 then
      show(file)
    end
  end,
})

return {}
