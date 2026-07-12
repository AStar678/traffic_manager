package com.visiondrive.service.sms;

import com.aliyuncs.DefaultAcsClient;
import com.aliyuncs.IAcsClient;
import com.aliyuncs.dypnsapi.model.v20170525.SendSmsVerifyCodeRequest;
import com.aliyuncs.dypnsapi.model.v20170525.SendSmsVerifyCodeResponse;
import com.aliyuncs.profile.DefaultProfile;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

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
    public void initialize() {
        requireConfigured("ALIYUN_ACCESS_KEY_ID", accessKeyId);
        requireConfigured("ALIYUN_ACCESS_KEY_SECRET", accessKeySecret);
        requireConfigured("ALIYUN_SMS_SIGN_NAME", signName);
        requireConfigured("ALIYUN_SMS_TEMPLATE_CODE", templateCode);

        DefaultProfile profile = DefaultProfile.getProfile(regionId, accessKeyId, accessKeySecret);
        client = new DefaultAcsClient(profile);
        log.info("阿里云号码认证服务初始化成功: region={}, signName={}, templateCode={}",
                regionId, signName, templateCode);
    }

    @Override
    public boolean send(String phone, String code) {
        try {
            SendSmsVerifyCodeRequest request = new SendSmsVerifyCodeRequest();
            request.setPhoneNumber(phone);
            request.setSignName(signName);
            request.setTemplateCode(templateCode);
            request.setTemplateParam("{\"code\":\"" + code + "\",\"min\":\"5\"}");
            request.setCodeType(1L);
            request.setCodeLength(6L);
            request.setValidTime(300L);

            SendSmsVerifyCodeResponse response = client.getAcsResponse(request);
            if ("OK".equals(response.getCode())) {
                log.info("阿里云短信发送成功: phone={}", maskPhone(phone));
                return true;
            }
            log.error("阿里云短信发送失败: phone={}, code={}, message={}",
                    maskPhone(phone), response.getCode(), response.getMessage());
            return false;
        } catch (Exception exception) {
            log.error("阿里云短信发送异常: phone={}", maskPhone(phone), exception);
            return false;
        }
    }

    private String maskPhone(String phone) {
        return phone.substring(0, 3) + "****" + phone.substring(phone.length() - 4);
    }

    private void requireConfigured(String environmentVariable, String value) {
        if (!StringUtils.hasText(value)) {
            throw new IllegalStateException("真实短信模式缺少环境变量: " + environmentVariable);
        }
    }
}
