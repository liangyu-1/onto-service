package com.onto.oaas.agent.operational;

import com.onto.oaas.agent.core.AbstractAgent;
import com.onto.oaas.agent.core.AgentBus;
import com.onto.oaas.agent.core.AgentMessage;
import com.onto.oaas.agent.core.AgentMessageType;
import java.util.List;
import java.util.Map;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * 学习排序（LTR）训练 Agent。
 *
 * <p>职责：定期从 FeedbackCollectorAgent 获取用户反馈数据，
 * 训练排序模型（LambdaMART），更新 RerankAgent 的排序策略。</p>
 *
 * <p>当前为框架实现，模型训练逻辑可接入外部 ML 服务（Python）。</p>
 *
 * <p>输入：{@link AgentMessageType#LTR_MODEL_UPDATE}（手动触发）</p>
 * <p>输出：{@link AgentMessageType#METRICS_RECORD}（训练完成通知）</p>
 */
@Slf4j
@Component
public class LTRTrainingAgent extends AbstractAgent {

    private final FeedbackCollectorAgent feedbackCollector;
    private volatile LTRModel currentModel;

    public LTRTrainingAgent(AgentBus agentBus, FeedbackCollectorAgent feedbackCollector) {
        super(agentBus);
        this.feedbackCollector = feedbackCollector;
        this.currentModel = LTRModel.defaultModel();
        subscribeTo(AgentMessageType.LTR_MODEL_UPDATE);
    }

    @Override
    public String getName() {
        return "LTRTrainingAgent";
    }

    @Override
    protected void onMessage(AgentMessage message) {
        log.info("[{}] Manual LTR model update triggered, correlationId={}",
                getName(), message.getCorrelationId());
        trainModel();
    }

    /**
     * 定时训练：每天凌晨 2 点执行。
     */
    @Scheduled(cron = "0 0 2 * * ?")
    public void scheduledTraining() {
        log.info("[{}] Scheduled LTR model training started", getName());
        trainModel();
    }

    /**
     * 训练排序模型。
     */
    private void trainModel() {
        Map<String, FeedbackCollectorAgent.UserFeedback> feedbacks = feedbackCollector.getFeedbackStore();
        if (feedbacks.size() < 100) {
            log.info("[{}] Insufficient feedback data ({} records), skipping training", getName(), feedbacks.size());
            return;
        }

        log.info("[{}] Training LTR model with {} feedback records", getName(), feedbacks.size());

        // TODO: 接入真实 ML 训练（调用 Python 服务或 Java ML 库）
        // 当前为模拟：根据反馈数据调整权重
        LTRModel newModel = trainFromFeedback(feedbacks);
        this.currentModel = newModel;

        log.info("[{}] LTR model updated: weights={}", getName(), newModel);

        // 通知 RerankAgent 模型更新
        AgentMessage updateMsg = AgentMessage.builder()
                .type(AgentMessageType.METRICS_RECORD)
                .build();
        updateMsg.putPayload("event", "ltr_model_updated");
        updateMsg.putPayload("model", newModel);
        publish(updateMsg);
    }

    /**
     * 基于反馈数据训练模型（简化版：统计调整权重）。
     */
    private LTRModel trainFromFeedback(Map<String, FeedbackCollectorAgent.UserFeedback> feedbacks) {
        long clickCount = feedbacks.values().stream().filter(FeedbackCollectorAgent.UserFeedback::isClicked).count();
        long totalCount = feedbacks.size();
        double ctr = totalCount > 0 ? (double) clickCount / totalCount : 0.0;

        // 简单启发式：CTR 高时增加向量权重（语义匹配更重要）
        double vectorWeight = 0.15 + ctr * 0.2;  // 0.15 ~ 0.35
        double keywordWeight = 0.25;
        double exactWeight = 0.25;
        double structureWeight = 0.2;
        double typeMatchWeight = 0.1;

        // 归一化
        double sum = exactWeight + keywordWeight + vectorWeight + structureWeight + typeMatchWeight;

        return new LTRModel(
                exactWeight / sum,
                keywordWeight / sum,
                vectorWeight / sum,
                structureWeight / sum,
                typeMatchWeight / sum
        );
    }

    public LTRModel getCurrentModel() {
        return currentModel;
    }

    /**
     * LTR 排序模型定义。
     */
    public record LTRModel(double wExact, double wKeyword, double wVector, double wStructure, double wTypeMatch) {
        public static LTRModel defaultModel() {
            return new LTRModel(0.3, 0.2, 0.2, 0.2, 0.1);
        }
    }
}
