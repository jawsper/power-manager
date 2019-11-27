import dbus
import os
import asyncio
import aiofiles

AC_PATH = '/sys/class/power_supply/AC/online'

async def toggle_backlight(high=None):
    process = await asyncio.create_subprocess_exec('/home/jasper/.local/bin/blcontrol', 'high' if high else 'low')
    return_code = await process.wait()
    print(f'blcontrol returns {return_code}')

async def get_current_ac_status():
    async with aiofiles.open(AC_PATH, 'r') as f:
        ac_connected = bool(int(await f.read()))
    return ac_connected

def inhibit_power_button():
    bus = dbus.SystemBus()
    proxy = bus.get_object('org.freedesktop.login1', '/org/freedesktop/login1')
    fd = proxy.Inhibit('handle-power-key', 'power-key-inhibitor', 'Override power key behaviour', 'block', dbus_interface='org.freedesktop.login1.Manager')
    return os.fdopen(fd.take(), 'r')

async def main():
    print('main')

    lock = inhibit_power_button()

    acpi_r, acpi_w = await asyncio.open_unix_connection(path='/var/run/acpid.socket')

    ac_connected = await get_current_ac_status()
    print(f"AC status: {ac_connected}")
    await toggle_backlight(ac_connected)

    try:
        while True:
            line = (await acpi_r.readline()).decode('utf-8').strip()
            line_items = line.split(' ')
            print('acpi:', line_items)
            if line_items[0:2] == ['button/power', 'PBTN']:
                process = await asyncio.create_subprocess_exec('/usr/bin/notify-send', 'Power button', 'Pressed', '-i', 'dialog-information', '-t', '1000')
                await process.wait()
            elif line_items[0] == 'button/lid' and line_items[2] == 'open':
                ac_connected = await get_current_ac_status()
                await toggle_backlight(ac_connected)
            elif line_items[0] == 'ac_adapter':
                ac_connected = bool(int(line_items[3]))
                print('ac connected:', ac_connected)
                await toggle_backlight(ac_connected)
    finally:
        lock.close()
        acpi_w.close()
        await acpi_w.wait_closed()

        print('the end')


if __name__ == '__main__':
    asyncio.run(main())