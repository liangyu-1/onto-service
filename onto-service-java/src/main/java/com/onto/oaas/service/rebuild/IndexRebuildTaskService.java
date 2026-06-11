package com.onto.oaas.service.rebuild;

import com.onto.oaas.model.RebuildTask;
import com.onto.oaas.model.enums.RebuildScope;
import com.onto.oaas.model.enums.RebuildStatus;
import com.onto.oaas.model.enums.TBoxObjectType;
import com.onto.oaas.repository.mybatis.RebuildTaskMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.autoconfigure.condition.ConditionalOnBean;
import org.springframework.stereotype.Service;

import javax.sql.DataSource;
import java.time.Instant;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@ConditionalOnBean(DataSource.class)
public class IndexRebuildTaskService {
    private final RebuildTaskMapper rebuildTaskMapper;
    private final IndexRebuildExecutor executor;

    public RebuildTask submitRebuildTask(TBoxObjectType objectType, RebuildScope scope) {
        RebuildTask task = RebuildTask.builder()
            .taskId(UUID.randomUUID().toString())
            .objectType(objectType)
            .scope(scope)
            .status(RebuildStatus.PENDING)
            .createdTime(Instant.now())
            .build();
        rebuildTaskMapper.insert(task);
        executor.executeRebuild(task.getTaskId(), objectType, scope);
        return task;
    }

    public RebuildStatus getTaskStatus(String taskId) {
        RebuildTask task = rebuildTaskMapper.selectById(taskId);
        return task != null ? task.getStatus() : null;
    }
}
