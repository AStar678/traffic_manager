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
            SendSmsVerifyCodeRequest req = new SendSmsVerifyCodeRequest();
            req.setPhoneNumber(phone);
            req.setSignName(signName);
            req.setTemplateCode(templateCode);
            req.setTemplateParam("{\"code\":\"" + code + "\",\"min\":\"5\"}");
            req.setCodeType(1L);
            req.setCodeLength(6L);
            req.setValidTime(300L);
            SendSmsVerifyCodeResponse resp = client.getAcsResponse(req);
            if ("OK".equals(resp.getCode())) {
                log.info("短信发送成功: phone={}, bizId={}", phone.substring(0, 3) + "****", resp.getModel().getBizId());
                return true;
            }
            log.error("短信发送失败: phone={}, code={}, msg={}", phone.substring(0, 3) + "****", resp.getCode(), resp.getMessage());
            return false;
        } catch (Exception e) {
            log.error("短信发送异常: phone={}", phone.substring(0, 3) + "****", e);
            return false;
        }
    }
}
