# SO101 Host Architecture Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the current SO101 MES/bringup stack into a maintainable operator-host architecture with clear boundaries between UI presentation, runtime communication, domain safety logic, and ROS execution.

**Architecture:** Keep the existing Vue + Spring Boot + ROS2 stack and refactor in place instead of rewriting. The target is a practical five-part split: `View`, `Presenter/ViewModel-style UI model`, `Communication Service`, `Domain/Application Logic`, and `Model/Store`. This is not a dogmatic MVVM rewrite; the rule is simpler: UI keeps presentation logic, communication is isolated, domain rules are isolated, and safety-critical state transitions are traceable and testable.

**Tech Stack:** Vue 3 + Vite, Spring Boot 3 / Java 17, ROS2 Humble / Python 3, node built-in test runner, Maven Surefire, Python `unittest`, local shell bringup scripts.

---

### Task 1: Lock Current Behavior With Characterization Tests

**Files:**
- Create: `mes_backend/src/test/java/com/so101/mes/service/SystemControlServiceStatusContractTest.java`
- Create: `mes_frontend/src/composables/__tests__/useMesBackend.contract.test.js`
- Create: `src/so101_bringup/test/test_task_executor_contract.py`
- Modify: `mes_backend/pom.xml`
- Modify: `mes_frontend/package.json`

**Step 1: Write the failing backend status contract test**

```java
@Test
void returns_protective_stop_when_estop_is_active() throws Exception {
  var service = TestSystemControlFactory.withRuntimeFiles("""
      {"online":true,"powerState":"已上电","estopActive":true,"allowExecute":true,"updatedAt":"2026-04-02T10:00:00+08:00"}
      """);

  SystemStatus status = service.getStatus();

  assertEquals("PROTECTIVE_STOP", status.realHardware().safetyState());
  assertFalse(status.realHardware().allowExecute());
  assertEquals("ESTOP_ACTIVE", status.realHardware().gateReasonCode());
}
```

**Step 2: Run test to verify it fails**

Run: `cd mes_backend && mvn -q -Dtest=SystemControlServiceStatusContractTest test`
Expected: FAIL because the test fixture/helper does not exist yet.

**Step 3: Add the minimal test fixture and backend assertions**

```java
final class TestSystemControlFactory {
  static SystemControlService withRuntimeFiles(String statusJson) {
    // Creates temp runtime dir + writes status/gate/calibration fixtures.
    throw new UnsupportedOperationException("implement in refactor task");
  }
}
```

**Step 4: Write the failing frontend and ROS contract tests**

```js
test('useMesBackend keeps transport failure out of component code', async () => {
  const events = [];
  const apiBase = { value: 'http://127.0.0.1:8080' };
  const model = useMesBackend(apiBase, { pushEvent: (...args) => events.push(args) });
  global.fetch = async () => ({ ok: false, status: 500, statusText: 'boom' });
  await model.refreshSystemStatus();
  assert.equal(events.at(-1)[0], 'warn');
});
```

```python
class TaskExecutorContractTests(unittest.TestCase):
    def test_command_locked_returns_error_status(self):
        # Extract helper during implementation so this test can execute without ROS spin.
        self.assertTrue(True)
```

**Step 5: Run the full characterization set**

Run: `cd mes_frontend && node --test src/composables/__tests__/useMesBackend.contract.test.js`
Expected: FAIL until the composable test seam exists.

Run: `python3 -m unittest discover -s src/so101_bringup/test -p 'test_task_executor_contract.py' -v`
Expected: FAIL until the executor logic is split from the ROS node shell.

**Step 6: Commit**

```bash
git add mes_backend/pom.xml \
  mes_backend/src/test/java/com/so101/mes/service/SystemControlServiceStatusContractTest.java \
  mes_frontend/package.json \
  mes_frontend/src/composables/__tests__/useMesBackend.contract.test.js \
  src/so101_bringup/test/test_task_executor_contract.py
git commit -m "test: add characterization coverage for host refactor"
```

### Task 2: Extract Real Hardware Safety Domain From `SystemControlService`

**Files:**
- Create: `mes_backend/src/main/java/com/so101/mes/model/GateReasonCode.java`
- Create: `mes_backend/src/main/java/com/so101/mes/service/realhardware/RuntimeRealHardwareReader.java`
- Create: `mes_backend/src/main/java/com/so101/mes/service/realhardware/CalibrationAssessmentService.java`
- Create: `mes_backend/src/main/java/com/so101/mes/service/realhardware/SafetyPolicyService.java`
- Create: `mes_backend/src/test/java/com/so101/mes/service/realhardware/SafetyPolicyServiceTest.java`
- Modify: `mes_backend/src/main/java/com/so101/mes/service/SystemControlService.java`
- Modify: `mes_backend/src/main/java/com/so101/mes/model/RealHardwareStatus.java`

**Step 1: Write the failing domain policy test**

```java
@Test
void uncalibrated_and_not_homed_forces_locked_state() {
  var payload = new RuntimeRealHardwareSnapshot(true, "已接入", "已上电", false, true, "2026-04-02T10:00:00+08:00");
  var calibration = CalibrationAssessment.uncalibrated();
  var gate = new CommandGateSnapshot(false, GateReasonCode.CAL_002_PENDING, "未校准禁止执行");

  var result = policy.assess(payload, calibration, gate);

  assertEquals("LOCKED", result.safetyState());
  assertFalse(result.allowExecute());
  assertEquals(GateReasonCode.UNCALIBRATED, result.gateReasonCode());
}
```

**Step 2: Run test to verify it fails**

Run: `cd mes_backend && mvn -q -Dtest=SafetyPolicyServiceTest test`
Expected: FAIL because the new service and enum do not exist.

**Step 3: Implement the minimal safety domain objects**

```java
public enum GateReasonCode {
  ESTOP_ACTIVE,
  WAITING_FOR_HARDWARE,
  STATUS_TIMEOUT,
  NOT_POWERED,
  UNCALIBRATED,
  CALIBRATION_INVALID,
  NOT_HOMED,
  MANUAL_LOCK,
  READY_FOR_MIN_MOTION
}
```

```java
public final class SafetyPolicyService {
  public SafetyAssessment assess(
      RuntimeRealHardwareSnapshot payload,
      CalibrationAssessment calibration,
      CommandGateSnapshot gate) {
    // Move all allowExecute / safetyState / checklist rules here.
    throw new UnsupportedOperationException("implement in refactor task");
  }
}
```

**Step 4: Route `SystemControlService` through the new reader + policy**

```java
RealHardwareStatus realHardware = realHardwareReader.read(
    realHardwareStatusFile,
    realHardwareCommandGateFile,
    realHardwareCalibrationFile
);
```

Goal:
- `SystemControlService` keeps orchestration only.
- Gate reason enum is the only source of truth.
- `allowExecute=false` is enforced for estop, offline, timeout, not powered, uncalibrated, and not homed.

**Step 5: Run the backend test suite**

Run: `cd mes_backend && mvn -q test`
Expected: PASS, with safety rules covered outside `SystemControlService`.

**Step 6: Commit**

```bash
git add mes_backend/src/main/java/com/so101/mes/model/GateReasonCode.java \
  mes_backend/src/main/java/com/so101/mes/service/realhardware \
  mes_backend/src/main/java/com/so101/mes/service/SystemControlService.java \
  mes_backend/src/main/java/com/so101/mes/model/RealHardwareStatus.java \
  mes_backend/src/test/java/com/so101/mes/service/realhardware/SafetyPolicyServiceTest.java
git commit -m "refactor: extract real hardware safety domain"
```

### Task 3: Split Runtime Process Control From Status Assembly

**Files:**
- Create: `mes_backend/src/main/java/com/so101/mes/service/runtime/SimulationRuntimeService.java`
- Create: `mes_backend/src/main/java/com/so101/mes/service/runtime/BrowserRuntimeService.java`
- Create: `mes_backend/src/main/java/com/so101/mes/service/runtime/RuntimeStatusService.java`
- Create: `mes_backend/src/test/java/com/so101/mes/service/runtime/SimulationRuntimeServiceTest.java`
- Modify: `mes_backend/src/main/java/com/so101/mes/service/SystemControlService.java`
- Modify: `mes_backend/src/main/java/com/so101/mes/controller/SystemControlController.java`

**Step 1: Write the failing runtime service test**

```java
@Test
void start_simulation_is_idempotent_when_pid_or_process_exists() throws Exception {
  when(runner.hasProcess("gzserver")).thenReturn(true);

  var status = simulationRuntimeService.startSimulation();

  verify(runner, never()).spawnBash(anyString(), any(), anyMap(), any());
  assertTrue(status.simRunning());
}
```

**Step 2: Run test to verify it fails**

Run: `cd mes_backend && mvn -q -Dtest=SimulationRuntimeServiceTest test`
Expected: FAIL because `SimulationRuntimeService` does not exist.

**Step 3: Implement the runtime services**

```java
public final class SimulationRuntimeService {
  public RuntimeProcessSnapshot startSimulation() throws IOException { ... }
  public RuntimeProcessSnapshot stopSimulation() throws IOException, InterruptedException { ... }
}
```

```java
public final class BrowserRuntimeService {
  public RuntimeProcessSnapshot openBrowser() throws IOException { ... }
  public RuntimeProcessSnapshot stopBrowser() throws IOException, InterruptedException { ... }
}
```

**Step 4: Reduce `SystemControlService` to a facade**

Target state:
- `SystemControlService.getStatus()` delegates to `RuntimeStatusService`.
- `startSimulation/openBrowser/...` delegate to runtime services.
- `SystemControlController` API contract stays unchanged.

**Step 5: Run backend regression**

Run: `cd mes_backend && mvn -q test`
Expected: PASS, with no API surface change under `/api/system/*`.

**Step 6: Commit**

```bash
git add mes_backend/src/main/java/com/so101/mes/service/runtime \
  mes_backend/src/main/java/com/so101/mes/service/SystemControlService.java \
  mes_backend/src/main/java/com/so101/mes/controller/SystemControlController.java \
  mes_backend/src/test/java/com/so101/mes/service/runtime/SimulationRuntimeServiceTest.java
git commit -m "refactor: split runtime process control from status assembly"
```

### Task 4: Split Frontend API, UI Model, And Event Narration

**Files:**
- Create: `mes_frontend/src/api/systemApi.js`
- Create: `mes_frontend/src/api/ordersApi.js`
- Create: `mes_frontend/src/api/rosApi.js`
- Create: `mes_frontend/src/api/workbenchApi.js`
- Create: `mes_frontend/src/composables/useSystemRuntimeModel.js`
- Create: `mes_frontend/src/composables/useOrderWorkflowModel.js`
- Create: `mes_frontend/src/composables/__tests__/useSystemRuntimeModel.test.js`
- Modify: `mes_frontend/src/composables/useMesBackend.js`

**Step 1: Write the failing UI model test**

```js
test('useSystemRuntimeModel exposes busy flags without owning fetch details', async () => {
  const calls = [];
  const api = {
    fetchSystemStatus: async () => ({ simRunning: true, gazeboRunning: true, realHardware: { allowExecute: false } }),
    startSimulation: async () => { calls.push('start'); return { status: { simRunning: true } }; },
  };

  const model = useSystemRuntimeModel({ api, pushEvent: () => {} });
  await model.startSimulation();

  assert.equal(calls[0], 'start');
  assert.equal(model.systemStatus.value.simRunning, true);
});
```

**Step 2: Run test to verify it fails**

Run: `cd mes_frontend && node --test src/composables/__tests__/useSystemRuntimeModel.test.js`
Expected: FAIL because the new API/model split does not exist.

**Step 3: Implement API wrappers and UI models**

```js
export function createSystemApi(apiBase) {
  return {
    fetchSystemStatus: () => fetchJson(apiBase, '/api/system/status'),
    startSimulation: () => postJson(apiBase, '/api/system/start-sim'),
    openRviz: () => postJson(apiBase, '/api/system/open-rviz'),
  };
}
```

```js
export function useSystemRuntimeModel({ api, pushEvent }) {
  const systemStatus = ref(defaultSystemStatus());
  const busy = ref(defaultBusyState());
  return { systemStatus, busy, startSimulation, refreshSystemStatus };
}
```

**Step 4: Shrink `useMesBackend.js` into a compatibility facade or remove it**

Target state:
- fetch and endpoint wiring live in `src/api/*`
- page/workflow state lives in `useSystemRuntimeModel` and `useOrderWorkflowModel`
- `pushEvent` happens at orchestration edges, not inside every low-level transport function

**Step 5: Run frontend regression**

Run: `cd mes_frontend && npm test`
Expected: PASS, including existing lib tests and the new composable test.

**Step 6: Commit**

```bash
git add mes_frontend/src/api \
  mes_frontend/src/composables/useSystemRuntimeModel.js \
  mes_frontend/src/composables/useOrderWorkflowModel.js \
  mes_frontend/src/composables/useMesBackend.js \
  mes_frontend/src/composables/__tests__/useSystemRuntimeModel.test.js
git commit -m "refactor: split frontend api transport from ui models"
```

### Task 5: Reduce `App.vue` To Page Composition Only

**Files:**
- Create: `mes_frontend/src/composables/useConsoleWorkspace.js`
- Create: `mes_frontend/src/composables/__tests__/useConsoleWorkspace.test.js`
- Modify: `mes_frontend/src/App.vue`
- Modify: `mes_frontend/src/composables/useRealtimeFeed.js`
- Modify: `mes_frontend/src/components/DeveloperWorkbenchPage.vue`

**Step 1: Write the failing workspace orchestration test**

```js
test('useConsoleWorkspace owns polling and live-runtime orchestration', async () => {
  const events = [];
  const workspace = useConsoleWorkspace({
    systemRuntime: fakeRuntimeModel(),
    orderWorkflow: fakeOrderWorkflowModel(),
    realtimeFeed: fakeRealtimeFeed(),
    pushEvent: (...args) => events.push(args),
  });

  await workspace.onMountedInit();
  assert.equal(events[0][1], '演示舱已就绪');
});
```

**Step 2: Run test to verify it fails**

Run: `cd mes_frontend && node --test src/composables/__tests__/useConsoleWorkspace.test.js`
Expected: FAIL because the orchestration composable does not exist.

**Step 3: Implement the workspace composable**

```js
export function useConsoleWorkspace(deps) {
  const activeTab = ref('console');
  const drawerOpen = ref(false);
  let pollTimer = null;
  async function onMountedInit() { ... }
  function onUnmountedCleanup() { ... }
  return { activeTab, drawerOpen, onMountedInit, onUnmountedCleanup };
}
```

**Step 4: Trim `App.vue`**

Target state:
- `App.vue` only wires components and delegates actions.
- polling timer setup/teardown leaves `App.vue`
- WebSocket connection sequencing leaves `App.vue`
- status derivation remains in dedicated helpers/composables

**Step 5: Run frontend regression**

Run: `cd mes_frontend && npm test`
Expected: PASS, with `App.vue` reduced to shell composition.

**Step 6: Commit**

```bash
git add mes_frontend/src/App.vue \
  mes_frontend/src/composables/useConsoleWorkspace.js \
  mes_frontend/src/composables/useRealtimeFeed.js \
  mes_frontend/src/composables/__tests__/useConsoleWorkspace.test.js \
  mes_frontend/src/components/DeveloperWorkbenchPage.vue
git commit -m "refactor: move console orchestration out of App shell"
```

### Task 6: Split ROS Task Executor Into Testable Services

**Files:**
- Create: `src/so101_bringup/scripts/task_status_publisher.py`
- Create: `src/so101_bringup/scripts/trajectory_builder.py`
- Create: `src/so101_bringup/scripts/detection_trigger_policy.py`
- Create: `src/so101_bringup/scripts/task_execution_service.py`
- Create: `src/so101_bringup/test/test_detection_trigger_policy.py`
- Create: `src/so101_bringup/test/test_trajectory_builder.py`
- Create: `src/so101_bringup/test/test_task_execution_service.py`
- Modify: `src/so101_bringup/scripts/task_executor.py`

**Step 1: Write the failing policy and builder tests**

```python
class DetectionTriggerPolicyTests(unittest.TestCase):
    def test_same_category_respects_cooldown(self):
        policy = DetectionTriggerPolicy(enabled=True, threshold=0.5, cooldown_sec=8.0, template_map={"red": "pick_place_red"})
        first = policy.try_trigger([("red", 0.9)], busy=False, now=100.0)
        second = policy.try_trigger([("red", 0.9)], busy=False, now=103.0)
        self.assertEqual(first.template_id, "pick_place_red")
        self.assertIsNone(second)
```

```python
class TrajectoryBuilderTests(unittest.TestCase):
    def test_builds_multi_point_joint_trajectory(self):
        msg, duration = build_mapped_trajectory_message({"planned_trajectory": {"joint_names": ["a"], "points": [{"positions": [1.0], "t": 0.8}]}})
        self.assertEqual(msg.joint_names, ["a"])
        self.assertAlmostEqual(duration, 0.8)
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m unittest discover -s src/so101_bringup/test -p 'test_detection_trigger_policy.py' -v`
Expected: FAIL because the policy module does not exist.

Run: `python3 -m unittest discover -s src/so101_bringup/test -p 'test_trajectory_builder.py' -v`
Expected: FAIL because the builder module does not exist.

**Step 3: Implement the extracted services**

```python
@dataclass
class TriggerDecision:
    category: str
    template_id: str
    request_id: str
```

```python
class TaskExecutionService:
    def execute(self, request_id: str, template_id: str, params: Optional[Dict] = None) -> None:
        # Pure execution flow without ROS subscription boilerplate.
        raise NotImplementedError
```

**Step 4: Reduce `task_executor.py` to ROS node wiring**

Target state:
- subscriptions/publishers stay in `task_executor.py`
- cooldown / category matching moves to `detection_trigger_policy.py`
- trajectory message construction moves to `trajectory_builder.py`
- status payload formatting moves to `task_status_publisher.py`
- execution flow moves to `task_execution_service.py`

**Step 5: Run ROS-side regression**

Run: `python3 -m unittest discover -s src/so101_bringup/test -p 'test_*.py' -v`
Expected: PASS, with most executor logic testable without spinning a ROS node.

**Step 6: Commit**

```bash
git add src/so101_bringup/scripts/task_status_publisher.py \
  src/so101_bringup/scripts/trajectory_builder.py \
  src/so101_bringup/scripts/detection_trigger_policy.py \
  src/so101_bringup/scripts/task_execution_service.py \
  src/so101_bringup/scripts/task_executor.py \
  src/so101_bringup/test/test_detection_trigger_policy.py \
  src/so101_bringup/test/test_trajectory_builder.py \
  src/so101_bringup/test/test_task_execution_service.py
git commit -m "refactor: split ros task executor into services"
```

### Task 7: Final Integration, Docs, And Acceptance Gate

**Files:**
- Modify: `docs/任务清单.md`
- Modify: `docs/进度日志.md`
- Create: `docs/generated/so101-host-architecture-overview.md`

**Step 1: Write the failing acceptance checklist**

```markdown
- [ ] Change backend protocol handling without touching Vue components
- [ ] Change hardware gate rules without touching process launch code
- [ ] Change ROS detection trigger policy without editing ROS node wiring
- [ ] Trace a failed execution from UI event -> backend gate -> ROS status
```

**Step 2: Run system verification commands**

Run: `cd mes_backend && mvn -q test`
Expected: PASS

Run: `cd mes_frontend && npm test`
Expected: PASS

Run: `python3 -m unittest discover -s src/so101_bringup/test -p 'test_*.py' -v`
Expected: PASS

**Step 3: Run the local demo smoke**

Run:

```bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws
bash tools/e2e/stop_visible_demo_stack.sh
bash tools/e2e/start_visible_demo_stack.sh
```

Expected:
- frontend loads without architecture regressions
- `/api/system/status` still returns the same contract
- real hardware card still renders protective state correctly

**Step 4: Update project tracking docs**

Record:
- which refactor subtasks landed
- what tests were added
- what remains intentionally deferred

**Step 5: Commit**

```bash
git add docs/任务清单.md docs/进度日志.md docs/generated/so101-host-architecture-overview.md
git commit -m "docs: record host architecture refactor rollout"
```

## Acceptance Standard

This refactor is complete only when all are true:

- `App.vue` no longer owns polling, connection sequencing, and workflow state directly.
- `useMesBackend.js` is removed or reduced to a compatibility wrapper.
- `SystemControlService` no longer contains safety rule implementation details.
- Gate reasons are enum-backed and reused consistently across backend and frontend contract output.
- `task_executor.py` is a thin ROS node shell, not the primary home of trigger policy and execution flow.
- A protocol change, device adapter change, or safety policy change can be made without editing unrelated UI files.

## Non-Goals

- Do not rewrite the UI visually.
- Do not replace Vue with another frontend pattern library.
- Do not big-bang replace Spring services with a new framework.
- Do not introduce hardware-only behavior that cannot be regression-tested without the arm present.

## Notes For The Implementer

- Prefer incremental commits exactly as listed above.
- Keep API response contracts stable while moving internals.
- When code changes land, update `docs/任务清单.md` and `docs/进度日志.md` in the same session per project rules.
- Treat this as a seam-by-seam refactor, not a cleanup sprint.
