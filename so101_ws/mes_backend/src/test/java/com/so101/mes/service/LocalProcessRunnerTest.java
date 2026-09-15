package com.so101.mes.service;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class LocalProcessRunnerTest {
  @Test
  void shouldNotReportMissingProcessAsRunning() {
    LocalProcessRunner runner = new LocalProcessRunner();

    boolean running = runner.hasProcess("so101-process-that-should-not-exist-9c1dca6c-0c2d-4fa9-b7ca-ecf9a82a9c5f");

    assertThat(running).isFalse();
  }
}
