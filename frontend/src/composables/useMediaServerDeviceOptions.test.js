import {describe, expect, it} from 'vitest'
import {mediaServerDeviceOptions} from './useMediaServerDeviceOptions.js'

describe('mediaServerDeviceOptions', () => {
    it('normalizes provider device shapes and filters invisible rows', () => {
        expect(mediaServerDeviceOptions([
            {Id: 'jf-tv', Name: 'Living Room', AppName: 'Jellyfin Android TV'},
            {ReportedDeviceId: 'emby-web', DeviceName: 'Browser', AppName: 'Emby Web'},
            {id: 'blank-name', name: ''},
            {Name: 'No id'},
        ])).toEqual([
            {value: 'jf-tv', label: 'Living Room / Jellyfin Android TV'},
            {value: 'emby-web', label: 'Browser / Emby Web'},
        ])
    })
})
