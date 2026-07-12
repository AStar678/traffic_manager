package com.visiondrive.service;

import com.visiondrive.model.dto.CarConfigurationRequest;
import com.visiondrive.model.entity.Car;
import com.visiondrive.model.entity.User;
import com.visiondrive.repository.CarRepository;
import com.visiondrive.repository.UserRepository;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Proxy;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;

class CarServiceTest {

    @Test
    void storesIndependentConfigurationPerAuthenticatedUserId() {
        Map<Long, User> users = new HashMap<>();
        users.put(1L, user(1L));
        users.put(2L, user(2L));
        Map<Long, Car> cars = new HashMap<>();

        UserRepository userRepository = proxy(UserRepository.class, (proxy, method, args) -> {
            if ("findById".equals(method.getName())) return Optional.ofNullable(users.get((Long) args[0]));
            return defaultValue(method.getReturnType());
        });
        CarRepository carRepository = proxy(CarRepository.class, (proxy, method, args) -> {
            if ("findByUserId".equals(method.getName())) return Optional.ofNullable(cars.get((Long) args[0]));
            if ("save".equals(method.getName())) {
                Car car = (Car) args[0];
                car.setId(car.getUser().getId());
                cars.put(car.getUser().getId(), car);
                return car;
            }
            return defaultValue(method.getReturnType());
        });

        CarService service = new CarService(carRepository, userRepository);
        service.updateCurrent(1L, configuration(21.0, 11));
        service.updateCurrent(2L, configuration(28.0, 88));

        assertEquals(11, service.getCurrent(1L).getAudioVolume());
        assertEquals(21.0, service.getCurrent(1L).getClimateTemperature());
        assertEquals(88, service.getCurrent(2L).getAudioVolume());
        assertEquals(28.0, service.getCurrent(2L).getClimateTemperature());
    }

    private static User user(Long id) {
        User user = new User();
        user.setId(id);
        user.setUsername("user-" + id);
        user.setPassword("unused");
        return user;
    }

    private static CarConfigurationRequest configuration(double temperature, int volume) {
        CarConfigurationRequest request = new CarConfigurationRequest();
        request.setClimateTemperature(temperature);
        request.setClimateMode("Auto");
        request.setAudioVolume(volume);
        request.setAudioTrack("Track");
        request.setSystemAwake(true);
        request.setActiveModule("驾驶");
        request.setPhoneStatus("待机");
        request.setPhoneCaller("无来电");
        request.setSpeed(0);
        request.setGear("P");
        request.setTireFrontLeft(2.4);
        request.setTireFrontRight(2.4);
        request.setTireRearLeft(2.3);
        request.setTireRearRight(2.3);
        return request;
    }

    @SuppressWarnings("unchecked")
    private static <T> T proxy(Class<T> type, java.lang.reflect.InvocationHandler handler) {
        return (T) Proxy.newProxyInstance(type.getClassLoader(), new Class<?>[]{type}, handler);
    }

    private static Object defaultValue(Class<?> type) {
        if (!type.isPrimitive()) return null;
        if (type == boolean.class) return false;
        if (type == byte.class) return (byte) 0;
        if (type == short.class) return (short) 0;
        if (type == int.class) return 0;
        if (type == long.class) return 0L;
        if (type == float.class) return 0F;
        if (type == double.class) return 0D;
        if (type == char.class) return '\0';
        return null;
    }
}
