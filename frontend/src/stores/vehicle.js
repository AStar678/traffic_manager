import { defineStore } from 'pinia'
import { mockVehicleState } from '@/utils/mockData'
import { getCurrentCar, updateCurrentCar } from '@/api/car'
import { useMusicStore } from '@/stores/music'

function initialVehicleState() {
  return {
    ...structuredClone(mockVehicleState),
    systemAwake: true,
    activeModule: '驾驶',
    lastGestureControl: null,
    controlHistory: []
  }
}

export const useVehicleStore = defineStore('vehicle', {
  state: () => ({
    vehicle: initialVehicleState(),
    loading: false,
    loaded: false
  }),
  getters: {
    lastGestureControl: state => state.vehicle.lastGestureControl,
    controlHistory: state => state.vehicle.controlHistory || []
  },
  actions: {
    applyGestureControl(control) {
      if (!control?.enabled || !control.actionType || control.actionType === 'NONE') return

      const musicStore = useMusicStore()

      const action = {
        gestureCode: control.gestureCode,
        gestureName: control.gestureName || '未知手势',
        actionType: control.actionType,
        actionLabel: control.actionLabel || '车辆控制',
        confidence: Number(control.confidence || 0),
        triggeredAt: Date.now()
      }

      switch (control.actionType) {
        case 'WAKE_SYSTEM':
          this.vehicle.systemAwake = true
          this.vehicle.activeModule = '驾驶'
          break
        case 'CONFIRM':
          this.vehicle.activeModule = '确认'
          break
        case 'VOLUME_UP':
          musicStore.setVolume(musicStore.volume + 8)
          this.vehicle.audio.volume = musicStore.volume
          this.vehicle.activeModule = '音乐'
          break
        case 'VOLUME_DOWN':
          musicStore.setVolume(musicStore.volume - 8)
          this.vehicle.audio.volume = musicStore.volume
          this.vehicle.activeModule = '音乐'
          break
        case 'NEXT_MEDIA':
          musicStore.next()
          this.vehicle.audio.track = musicStore.currentTrack?.title || this.vehicle.audio.track
          this.vehicle.activeModule = '音乐'
          break
        case 'CLIMATE_UP':
          this.vehicle.climate.temperature = Math.min(30, this.vehicle.climate.temperature + 1)
          this.vehicle.climate.mode = 'Manual'
          this.vehicle.activeModule = '空调'
          break
        case 'CLIMATE_DOWN':
          this.vehicle.climate.temperature = Math.max(16, this.vehicle.climate.temperature - 1)
          this.vehicle.climate.mode = 'Manual'
          this.vehicle.activeModule = '空调'
          break
        case 'ANSWER_CALL':
          this.vehicle.phone.status = '通话中'
          this.vehicle.phone.caller = '车主手势接听'
          this.vehicle.activeModule = '电话'
          break
        case 'HANG_UP':
          this.vehicle.phone.status = '待机'
          this.vehicle.phone.caller = '无来电'
          this.vehicle.activeModule = '驾驶'
          break
        case 'OPEN_NAVIGATION':
          this.vehicle.activeModule = '导航'
          break
        case 'RETURN_HOME':
          this.vehicle.activeModule = '驾驶'
          break
        default:
          break
      }

      this.vehicle.lastGestureControl = action
      this.vehicle.controlHistory = [action, ...(this.vehicle.controlHistory || [])].slice(0, 6)
      this.persist()
    },
    async loadCurrent() {
      if (!localStorage.getItem('token')) return
      this.loading = true
      try {
        const response = await getCurrentCar()
        this.applyServerConfiguration(response.data || response)
        this.loaded = true
      } catch (error) {
        console.warn('读取云端车辆配置失败', error)
      } finally {
        this.loading = false
      }
    },
    async persist() {
      if (!localStorage.getItem('token')) return
      try {
        const response = await updateCurrentCar(this.toServerConfiguration())
        this.applyServerConfiguration(response.data || response)
      } catch (error) {
        console.warn('保存云端车辆配置失败', error)
      }
    },
    toServerConfiguration() {
      const tires = Object.fromEntries((this.vehicle.tirePressure || []).map(item => [item.name, item.value]))
      return {
        climateTemperature: this.vehicle.climate.temperature,
        climateMode: this.vehicle.climate.mode,
        audioVolume: this.vehicle.audio.volume,
        audioTrack: this.vehicle.audio.track,
        systemAwake: Boolean(this.vehicle.systemAwake),
        activeModule: this.vehicle.activeModule || '驾驶',
        phoneStatus: this.vehicle.phone.status,
        phoneCaller: this.vehicle.phone.caller,
        speed: this.vehicle.speed,
        gear: this.vehicle.gear,
        tireFrontLeft: tires['左前'] ?? 2.4,
        tireFrontRight: tires['右前'] ?? 2.4,
        tireRearLeft: tires['左后'] ?? 2.3,
        tireRearRight: tires['右后'] ?? 2.1
      }
    },
    applyServerConfiguration(data) {
      if (!data) return
      Object.assign(this.vehicle, {
        speed: data.speed,
        gear: data.gear,
        systemAwake: data.systemAwake,
        activeModule: data.activeModule,
        climate: { temperature: data.climateTemperature, mode: data.climateMode },
        audio: { volume: data.audioVolume, track: data.audioTrack },
        phone: { status: data.phoneStatus, caller: data.phoneCaller },
        tirePressure: [
          { name: '左前', value: data.tireFrontLeft, status: tireStatus(data.tireFrontLeft) },
          { name: '右前', value: data.tireFrontRight, status: tireStatus(data.tireFrontRight) },
          { name: '左后', value: data.tireRearLeft, status: tireStatus(data.tireRearLeft) },
          { name: '右后', value: data.tireRearRight, status: tireStatus(data.tireRearRight) }
        ]
      })
    }
  }
})

function tireStatus(value) {
  return value < 2.2 || value > 2.8 ? 'warning' : 'normal'
}
