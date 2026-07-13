package com.visiondrive.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.visiondrive.model.dto.CameraSlotRequest;
import com.visiondrive.model.dto.CameraSlotResponse;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.test.util.ReflectionTestUtils;

import javax.imageio.ImageIO;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class CameraManagerServiceTest {

    @TempDir
    Path tempDir;

    private CameraManagerService service;
    private Path stateFile;

    @BeforeEach
    void setUp() {
        service = new CameraManagerService(new ObjectMapper());
        stateFile = tempDir.resolve("data/camera-slots.json");
        ReflectionTestUtils.setField(service, "stateFile", stateFile.toString());
        ReflectionTestUtils.setField(service, "sourceDir", tempDir.resolve("sources").toString());
        ReflectionTestUtils.setField(service, "frameDir", tempDir.resolve("frames").toString());
        service.initialize();
    }

    @AfterEach
    void tearDown() {
        service.shutdown();
    }

    @Test
    void storesStaticWeatherTextureFlagWithoutMutatingFrames() throws Exception {
        Path source = tempDir.resolve("source.png");
        BufferedImage original = new BufferedImage(640, 360, BufferedImage.TYPE_INT_RGB);
        Graphics2D graphics = original.createGraphics();
        graphics.setColor(new Color(122, 136, 148));
        graphics.fillRect(0, 0, original.getWidth(), original.getHeight());
        graphics.dispose();
        ImageIO.write(original, "png", source.toFile());

        CameraSlotRequest request = new CameraSlotRequest();
        request.setSourceType("IMAGE");
        request.setName("复杂天气测试");
        request.setPath(source.toString());
        service.updateSlot(1, request);

        BufferedImage dryFrame = ImageIO.read(service.captureSlot(1).path().toFile());
        BufferedImage rawFrameBeforeToggle = ImageIO.read(tempDir.resolve("frames/camera-1.jpg").toFile());
        CameraSlotResponse updated = service.updateWeatherSimulation(1, true);
        Path previewPath = service.currentFramePath(1);
        BufferedImage preview = ImageIO.read(previewPath.toFile());
        BufferedImage inferenceFrame = ImageIO.read(service.captureSlot(1).path().toFile());
        BufferedImage rawFrameAfterToggle = ImageIO.read(tempDir.resolve("frames/camera-1.jpg").toFile());

        assertThat(updated.getWeatherSimulationEnabled()).isTrue();
        assertThat(previewPath.getFileName().toString()).isEqualTo("camera-1.jpg");
        assertThat(meanPixelDifference(dryFrame, preview)).isZero();
        assertThat(meanPixelDifference(dryFrame, inferenceFrame)).isZero();
        assertThat(meanPixelDifference(rawFrameBeforeToggle, rawFrameAfterToggle)).isZero();
        assertThat(Files.readString(stateFile)).contains("\"weatherSimulationEnabled\" : true");
    }

    @Test
    void treatsLegacyStateWithoutWeatherFieldAsDisabled() throws Exception {
        String legacyState = """
                [
                  {"slotId":1,"name":"CAM 1","sourceType":"OFF","deviceIndex":0},
                  {"slotId":2,"name":"CAM 2","sourceType":"OFF","deviceIndex":0},
                  {"slotId":3,"name":"CAM 3","sourceType":"OFF","deviceIndex":0}
                ]
                """;
        service.shutdown();
        Files.createDirectories(stateFile.getParent());
        Files.writeString(stateFile, legacyState);

        service = new CameraManagerService(new ObjectMapper());
        ReflectionTestUtils.setField(service, "stateFile", stateFile.toString());
        ReflectionTestUtils.setField(service, "sourceDir", tempDir.resolve("legacy-sources").toString());
        ReflectionTestUtils.setField(service, "frameDir", tempDir.resolve("legacy-frames").toString());
        service.initialize();

        assertThat(service.listSlots())
                .extracting(CameraSlotResponse::getWeatherSimulationEnabled)
                .containsOnly(false);
    }

    @Test
    void refusesWeatherSimulationForAnInactiveSlot() {
        CameraSlotRequest request = new CameraSlotRequest();
        request.setSourceType("OFF");
        service.updateSlot(1, request);

        assertThatThrownBy(() -> service.updateWeatherSimulation(1, true))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("请先开启摄像头");
    }

    private double meanPixelDifference(BufferedImage first, BufferedImage second) {
        long difference = 0;
        for (int y = 0; y < first.getHeight(); y++) {
            for (int x = 0; x < first.getWidth(); x++) {
                Color firstColor = new Color(first.getRGB(x, y));
                Color secondColor = new Color(second.getRGB(x, y));
                difference += Math.abs(firstColor.getRed() - secondColor.getRed());
                difference += Math.abs(firstColor.getGreen() - secondColor.getGreen());
                difference += Math.abs(firstColor.getBlue() - secondColor.getBlue());
            }
        }
        return difference / (double) (first.getWidth() * first.getHeight() * 3L);
    }
}
