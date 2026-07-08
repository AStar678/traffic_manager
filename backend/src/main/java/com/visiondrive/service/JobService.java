package com.visiondrive.service;

import com.visiondrive.model.dto.JobRequest;
import com.visiondrive.model.dto.JobStatusResponse;
import com.visiondrive.model.entity.Job;
import com.visiondrive.repository.JobRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class JobService {

    private final JobRepository jobRepository;

    /**
     * 创建视频识别任务
     */
    public JobStatusResponse createJob(JobRequest request) {
        String jobId = "job_" + System.currentTimeMillis();

        Job job = new Job();
        job.setJobId(jobId);
        job.setTaskType(request.getTaskType());
        job.setInputUrl(request.getInput().getUrl());
        job.setStatus("queued");
        job.setProgress(0);
        job.setProcessedFrames(0);
        job.setTotalFrames(0);
        job.setUserId(1L);  // TODO: 从SecurityContext获取

        jobRepository.save(job);
        log.info("创建视频任务成功: jobId={}", jobId);

        // TODO: 实际调用算法服务的创建任务接口
        // algorithmClient.createVideoJob(request, callbackUrl);

        return new JobStatusResponse(jobId, "queued");
    }

    /**
     * 查询任务状态
     */
    public JobStatusResponse getJobStatus(String jobId) {
        Job job = jobRepository.findByJobId(jobId)
                .orElseThrow(() -> new RuntimeException("任务不存在: " + jobId));

        return new JobStatusResponse(
                job.getJobId(),
                job.getTaskType(),
                job.getStatus(),
                job.getProgress(),
                job.getProcessedFrames(),
                job.getTotalFrames(),
                job.getCreatedAt(),
                job.getUpdatedAt()
        );
    }

    /**
     * 取消任务
     */
    public JobStatusResponse cancelJob(String jobId) {
        Job job = jobRepository.findByJobId(jobId)
                .orElseThrow(() -> new RuntimeException("任务不存在: " + jobId));

        if ("completed".equals(job.getStatus()) || "cancelled".equals(job.getStatus())) {
            throw new RuntimeException("任务已完成或已取消，无法再次取消");
        }

        job.setStatus("cancelled");
        jobRepository.save(job);

        // TODO: 调用算法服务取消任务

        return new JobStatusResponse(jobId, "cancelled");
    }

    /**
     * 更新任务状态（供回调接口使用）
     */
    public void updateJobStatus(String jobId, String status, Integer progress,
                                Integer processedFrames, Integer totalFrames,
                                String resultUrl, String errorMessage) {
        Job job = jobRepository.findByJobId(jobId)
                .orElseThrow(() -> new RuntimeException("任务不存在: " + jobId));

        job.setStatus(status);
        if (progress != null) job.setProgress(progress);
        if (processedFrames != null) job.setProcessedFrames(processedFrames);
        if (totalFrames != null) job.setTotalFrames(totalFrames);
        if (resultUrl != null) job.setResultUrl(resultUrl);
        if (errorMessage != null) job.setErrorMessage(errorMessage);
        job.setUpdatedAt(LocalDateTime.now());

        jobRepository.save(job);
        log.info("任务状态更新: jobId={}, status={}, progress={}", jobId, status, progress);
    }
}