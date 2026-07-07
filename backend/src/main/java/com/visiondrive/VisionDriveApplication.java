package com.visiondrive;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.boot.autoconfigure.security.servlet.SecurityAutoConfiguration;


@SpringBootApplication(exclude = {SecurityAutoConfiguration.class})
@EnableScheduling
public class VisionDriveApplication {

    public static void main(String[] args) {

        SpringApplication.run(VisionDriveApplication.class, args);
    }
}
