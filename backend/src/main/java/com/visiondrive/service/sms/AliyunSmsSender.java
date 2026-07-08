package com.visiondrive.service.sms;

import com.aliyuncs.DefaultAcsClient;
import com.aliyuncs.IAcsClient;
import com.aliyuncs.dypnsapi.model.v20170525.SendSmsVerifyCodeRequest;
import com.aliyuncs.dypnsapi.model.v20170525.SendSmsVerifyCodeResponse;
import com.aliyuncs.profile.DefaultProfile;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import jakarta.annotation.PostConstruct;

/**
 * 阿里云号码认证服务 —— 短信验证码发送器
 * 使用系统赠送的签名和模板，无需自行审核
 */
@Slf4j
@Component
@ConditionalOnProperty(name = "sms.provider", havingValue = "aliyun")
public class AliyunSmsSender implements SmsSender {

    @Value("${sms.aliyun.access-key-id}")
    private String accessKeyId;

    @Value("${sms.aliyun.access-key-secret}")
    private String accessKeySecret;

    @Value("${sms.aliyun.region-id:cn-hangzhou}")
    private String regionId;

    @Value("${sms.aliyun.sign-name}")
    private String signName;

    @Value("${sms.aliyun.template-code}")
    private String templateCode;

    private IAcsClient client;

    @PostConstruct
    public void init() {
        DefaultProfile profile = DefaultProfile.getProfile(regionId, accessKeyId, accessKeySecret);
        this.client = new DefaultAcsClient(profile);
        log.info("阿里云号码认证服务初始化成功, region={}", regionId);
    }

    @Override
    public boolean send(String phone, String code) {
        try {
            SendSmsVerifyCodeRequest request = new SendSmsVerifyCodeRequest();
            request.setPhoneNumber(phone);
            request.setSignName(signName);
            request.setTemplateCode(templateCode);
            // 传入验证码和有效期（分钟），模板需要这两个变量
            request.setTemplateParam("{\"code\":\"" + code + "\",\"min\":\"5\"}");
            request.setCodeType(1L);   // 纯数字
            request.setCodeLength(6L); // 6 位
            request.setValidTime(300L); // 5 分钟有效

            SendSmsVerifyCodeResponse response = client.getAcsResponse(request);

            if ("OK".equals(response.getCode())) {
                log.info("短信发送成功: phone={}, bizId={}",
                        phone.substring(0, 3) + "****", response.getModel().getBizId());
                return true;
            } else {
                log.error("短信发送失败: phone={}, code={}, message={}",
                        phone.substring(0, 3) + "****", response.getCode(), response.getMessage());
                return false;
            }
        } catch (Exception e) {
            log.error("短信发送异常: phone={}", phone.substring(0, 3) + "****", e);
            return false;
        }
    }
}
