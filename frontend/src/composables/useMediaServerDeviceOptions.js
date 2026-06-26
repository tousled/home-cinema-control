export function mediaServerDeviceOptions(devices = []) {
    return devices
        .map(device => {
            const value = String(device.id || device.Id || device.ReportedDeviceId || '').trim()
            const name = String(device.name || device.Name || device.DeviceName || '').trim()
            const appName = String(device.app_name || device.appName || device.AppName || '').trim()
            const label = name && appName && !name.includes(appName) ? `${name} / ${appName}` : name
            return {value, label}
        })
        .filter(option => option.value && option.label)
}
