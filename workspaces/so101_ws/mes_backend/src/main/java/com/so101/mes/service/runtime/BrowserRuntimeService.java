package com.so101.mes.service.runtime;

import com.so101.mes.service.ProcessRunner;
import java.io.IOException;
import java.nio.file.Files;
import java.util.Map;

public final class BrowserRuntimeService {
  private final ProcessRunner runner;
  private final RuntimeStatusService runtimeStatusService;

  public BrowserRuntimeService(ProcessRunner runner, RuntimeStatusService runtimeStatusService) {
    this.runner = runner;
    this.runtimeStatusService = runtimeStatusService;
  }

  public RuntimeProcessSnapshot openBrowser() throws IOException {
    runtimeStatusService.ensureRuntimeDir();
    Long livePid = runtimeStatusService.readLivePid(runtimeStatusService.browserPidFile());
    if (livePid != null || runner.isPortListening(9223)) {
      return runtimeStatusService.getRuntimeSnapshot();
    }

    String command =
        "exec '%s'"
            .formatted(
                runtimeStatusService
                    .workspaceRoot()
                    .resolve("tools/browser/start_clean_cdp_browser.sh"));
    long pid =
        runner.spawnBash(
            command,
            runtimeStatusService.workspaceRoot(),
            Map.of(),
            runtimeStatusService.browserLogFile());
    runtimeStatusService.writePid(runtimeStatusService.browserPidFile(), pid);
    runtimeStatusService.waitForPortState(9223, true, 30, 200);
    return runtimeStatusService.getRuntimeSnapshot();
  }

  public RuntimeProcessSnapshot stopBrowser() throws IOException, InterruptedException {
    Long browserPid = runtimeStatusService.readLivePid(runtimeStatusService.browserPidFile());
    if (browserPid != null) {
      runner.terminate(browserPid);
    }

    runner.runBash(
        "exec '%s'"
            .formatted(
                runtimeStatusService
                    .workspaceRoot()
                    .resolve("tools/browser/stop_clean_cdp_browser.sh")),
        runtimeStatusService.workspaceRoot());
    runtimeStatusService.waitForPortState(9223, false, 20, 150);
    Files.deleteIfExists(runtimeStatusService.browserPidFile());
    return runtimeStatusService.getRuntimeSnapshot();
  }
}
