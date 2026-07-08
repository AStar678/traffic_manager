package com.visiondrive.service.sms;

/**
 * 短信发送器接口
 */
public interface SmsSender {

    /**
     * 发送验证码短信
     * @param phone  手机号
     * @param code   6位验证码
     * @return true=发送成功
     */
    boolean send(String phone, String code);
}
