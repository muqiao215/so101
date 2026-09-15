package com.so101.mes.service;

import java.io.IOException;
import java.nio.file.Path;
import java.util.Map;

public interface ProcessRunner {
  long spawnBash(String command, Path workdir, Map<String, String> env, Path logFile) throws IOException;

  int runBash(String command, Path workdir) throws IOException, InterruptedException;

  boolean hasProcess(String pattern);

  boolean isPortListening(int port);

  boolean isAlive(long pid);

  void terminate(long pid);
}
