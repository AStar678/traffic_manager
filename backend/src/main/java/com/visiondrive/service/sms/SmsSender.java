package com.visiondrive.service.sms;

public interface SmsSender {
    boolean send(String phone, String code);
}
