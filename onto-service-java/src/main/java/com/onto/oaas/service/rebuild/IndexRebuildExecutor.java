package com.onto.oaas.service.rebuild;

import com.onto.oaas.model.RebuildTask;
import com.onto.oaas.model.enums.RebuildScope;
import com.onto.oaas.model.enums.RebuildStatus;
import com.onto.oaas.model.enums.TBoxObjectType;
import com.onto.oaas.repository.TBoxGraphRepository;
import com.onto.oaas.repository.TBoxIndexRepository;
import com.onto.oaas.repository.mybatis.RebuildTaskMapper;
import com.onto.oaas.service.TBoxIndexBuilder;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnBean;
import org.springframework.stereotype.Component;

import javax.sql.DataSource;
import jakarta.annotation.PreDestroy;
import java.time.Instant;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@Component
@RequiredArgsConstructor
@Slf4j
@ConditionalOnBean(DataSource.class)
public class IndexRebuildExecutor {
    private final TBoxGraphRepository graphRepository;
    private final TBoxIndexRepository indexRepository;
    private final TBoxIndexBuilder indexBuilder;
    private final RebuildTaskMapper rebuildTaskMapper;
    private final ExecutorService executor = Executors.newFixedThreadPool(4);

    public void executeRebuild(String taskId, TBoxObjectType objectType, RebuildScope scope) {
        executor.submit(() -> {
            try {
                updateTaskStatus(taskId, RebuildStatus.RUNNING, null, null, null);
                indexRepository.rebuildIndex();
                updateTaskStatus(taskId, RebuildStatus.SUCCESS, 0L, 0L, null);
            } catch (Exception e) {
                log.error("Rebuild failed: taskId={}", taskId, e);
                updateTaskStatus(taskId, RebuildStatus.FAILED, null, null, e.getMessage());
            }
        });
    }

    private void updateTaskStatus(String taskId, RebuildStatus status, Long total, Long processed, String error) {
        RebuildTask task = rebuildTaskMapper.selectById(taskId);
        if (task != null) {
            task.setStatus(status);
            if (total != null) task.setTotalCount(total);
            if (processed != null) task.setProcessedCount(processed);
            if (error != null) task.setErrorMessage(error);
            if (status == RebuildStatus.RUNNING) task.setStartedTime(Instant.now());
            if (status == RebuildStatus.SUCCESS || status == RebuildStatus.FAILED) task.setCompletedTime(Instant.now());
            rebuildTaskMapper.updateById(task);
        }
    }

    @PreDestroy
    public void shutdown() {
        executor.shutdown();
    }
}
