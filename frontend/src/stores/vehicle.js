import { defineStore } from 'pinia'
import { mockVehicleState } from '@/utils/mockData'

const STORAGE_KEY = 'visiondrive.vehicle.state'

function initialVehicleState() {
  const snapshot = readStoredState()
  if (snapshot) return snapshot
  return {
    ...structuredClone(mockVehicleState),
    systemAwake: true,
    activeModule: '驾驶',
    lastGestureControl: null,
    controlHistory: []
  }
}

function readStoredState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch (error) {
    console.warn('读取车辆状态缓存失败', error)
    return null
  }
}

export const useVehicleStore = defineStore('vehicle', {
  state: () => ({
    vehicle: initialVehicleState()
  }),
  getters: {
    lastGestureControl: state => state.vehicle.lastGestureControl,
    controlHistory: state => state.vehicle.controlHistory || []
  },
  actions: {
    applyGestureControl(control) {
      if (!control?.enabled || !control.actionType || control.actionType === 'NONE') return

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
          this.vehicle.audio.volume = Math.min(100, this.vehicle.audio.volume + 8)
          this.vehicle.activeModule = '音乐'
          break
        case 'VOLUME_DOWN':
          this.vehicle.audio.volume = Math.max(0, this.vehicle.audio.volume - 8)
          this.vehicle.activeModule = '音乐'
          break
        case 'NEXT_MEDIA':
          this.vehicle.audio.track = nextTrack(this.vehicle.audio.track)
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
    persist() {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(this.vehicle))
      } catch (error) {
        console.warn('保存车辆状态缓存失败', error)
      }
    }
  }
})

function nextTrack(currentTrack) {
  const tracks = ['City Drive', 'Night Run', 'Signal Blue', 'Highway FM']
  const index = tracks.indexOf(currentTrack)
  return tracks[(index + 1) % tracks.length]
}
