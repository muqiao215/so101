package com.so101.mes.controller;

import com.so101.mes.service.WorkbenchService;
import com.so101.mes.service.WorkbenchService.WorkbenchMergeRequest;
import com.so101.mes.service.WorkbenchService.WorkbenchPreviewRequest;
import com.so101.mes.service.WorkbenchService.WorkbenchSaveRequest;
import java.io.IOException;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/workbench")
public class WorkbenchController {
  private final WorkbenchService workbenchService;

  public WorkbenchController(WorkbenchService workbenchService) {
    this.workbenchService = workbenchService;
  }

  @PostMapping("/preview")
  public Map<String, Object> previewPose(@RequestBody WorkbenchPreviewRequest request) {
    return workbenchService.previewPose(request);
  }

  @PostMapping("/save")
  public Map<String, Object> saveExport(@RequestBody WorkbenchSaveRequest request) throws IOException {
    return workbenchService.saveExport(request);
  }

  @PostMapping("/merge-waypoints")
  public Map<String, Object> mergeWaypoints(@RequestBody WorkbenchMergeRequest request)
      throws IOException {
    return workbenchService.mergeIntoWaypoints(request);
  }

  @GetMapping("/vision/latest-quality")
  public Map<String, Object> latestVisionQuality() throws IOException {
    return workbenchService.latestVisionQuality();
  }
}
