package com.visiondrive.service;

import com.visiondrive.common.exception.BusinessException;
import com.visiondrive.model.dto.CarConfigurationRequest;
import com.visiondrive.model.dto.CarResponse;
import com.visiondrive.model.entity.Car;
import com.visiondrive.model.entity.User;
import com.visiondrive.repository.CarRepository;
import com.visiondrive.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class CarService {
    private final CarRepository carRepository;
    private final UserRepository userRepository;

    @Transactional
    public CarResponse getCurrent(Long userId) {
        return toResponse(carRepository.findByUserId(userId).orElseGet(() -> createDefault(userId)));
    }

    @Transactional
    public CarResponse updateCurrent(Long userId, CarConfigurationRequest request) {
        Car car = carRepository.findByUserId(userId).orElseGet(() -> createDefault(userId));
        car.setClimateTemperature(request.getClimateTemperature());
        car.setClimateMode(request.getClimateMode());
        car.setAudioVolume(request.getAudioVolume());
        car.setAudioTrack(request.getAudioTrack());
        car.setSystemAwake(request.getSystemAwake());
        car.setActiveModule(request.getActiveModule());
        car.setPhoneStatus(request.getPhoneStatus());
        car.setPhoneCaller(request.getPhoneCaller());
        car.setSpeed(request.getSpeed());
        car.setGear(request.getGear());
        car.setTireFrontLeft(request.getTireFrontLeft());
        car.setTireFrontRight(request.getTireFrontRight());
        car.setTireRearLeft(request.getTireRearLeft());
        car.setTireRearRight(request.getTireRearRight());
        return toResponse(carRepository.save(car));
    }

    private Car createDefault(Long userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new BusinessException(404, "用户不存在"));
        Car car = new Car();
        car.setUser(user);
        return carRepository.save(car);
    }

    private CarResponse toResponse(Car car) {
        return new CarResponse(
                car.getId(),
                car.getClimateTemperature(),
                car.getClimateMode(),
                car.getAudioVolume(),
                car.getAudioTrack(),
                car.getSystemAwake(),
                car.getActiveModule(),
                car.getPhoneStatus(),
                car.getPhoneCaller(),
                car.getSpeed(),
                car.getGear(),
                car.getTireFrontLeft(),
                car.getTireFrontRight(),
                car.getTireRearLeft(),
                car.getTireRearRight(),
                car.getUpdatedAt()
        );
    }
}
