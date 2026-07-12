import request from './request'

export function getCurrentCar() {
  return request.get('/cars/current')
}

export function updateCurrentCar(configuration) {
  return request.put('/cars/current', configuration)
}
