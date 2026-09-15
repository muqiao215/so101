package com.so101.mes.service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import org.springframework.stereotype.Component;

@Component
public class LocalProcessRunner implements ProcessRunner {
  @Override
  public long spawnBash(String command, Path workdir, Map<String, String> env, Path logFile) throws IOException {
    Files.createDirectories(logFile.getParent());
    ProcessBuilder pb = new ProcessBuilder("bash", "-lc", command);
    pb.directory(workdir.toFile());
    pb.redirectErrorStream(true);
    pb.redirectOutput(ProcessBuilder.Redirect.appendTo(logFile.toFile()));
    pb.environment().putAll(env);
    Process process = pb.start();
    return process.pid();
  }

  @Override
  public int runBash(String command, Path workdir) throws IOException, InterruptedException {
    ProcessBuilder pb = new ProcessBuilder("bash", "-lc", command);
    pb.directory(workdir.toFile());
    Process process = pb.start();
    return process.waitFor();
  }

  @Override
  public boolean hasProcess(String pattern) {
    try {
      return ProcessHandle.allProcesses()
          .map(ProcessHandle::info)
          .map(info -> info.commandLine().orElse(info.command().orElse("")))
          .anyMatch(commandLine -> commandLine.contains(pattern));
    } catch (Exception e) {
      return false;
    }
  }

  @Override
  public boolean isPortListening(int port) {
    try {
      ProcessBuilder pb =
          new ProcessBuilder(
              "bash",
              "-lc",
              "lsof -iTCP:" + port + " -sTCP:LISTEN -P -n >/dev/null || curl -fsS --max-time 1 http://127.0.0.1:"
                  + port
                  + "/json/version >/dev/null");
      Process process = pb.start();
      return process.waitFor() == 0;
    } catch (Exception e) {
      return false;
    }
  }

  @Override
  public boolean isAlive(long pid) {
    return ProcessHandle.of(pid).map(ProcessHandle::isAlive).orElse(false);
  }

  @Override
  public void terminate(long pid) {
    ProcessHandle.of(pid).ifPresent(handle -> {
      handle.descendants().forEach(child -> {
        try {
          child.destroy();
        } catch (Exception ignored) {
        }
      });
      handle.destroy();
      try {
        Thread.sleep(300);
      } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
      }
      if (handle.isAlive()) {
        handle.descendants().forEach(child -> {
          try {
            child.destroyForcibly();
          } catch (Exception ignored) {
          }
        });
        handle.destroyForcibly();
      }
    });
  }
}
