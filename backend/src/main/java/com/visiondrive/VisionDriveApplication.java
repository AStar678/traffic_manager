package com.visiondrive;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class VisionDriveApplication {

    public static void main(String[] args) {
        SpringApplication.run(VisionDriveApplication.class, args);
    }
}
