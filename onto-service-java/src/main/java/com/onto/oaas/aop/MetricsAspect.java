package com.onto.oaas.aop;

import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.stereotype.Component;

@Aspect
@Component
public class MetricsAspect {
    private final MeterRegistry registry;
    public MetricsAspect(MeterRegistry registry) { this.registry = registry; }

    @Around("execution(* com.onto.oaas.service..*.*(..)) || execution(* com.onto.oaas.repository..*.*(..))")
    public Object recordMethodTime(ProceedingJoinPoint pjp) throws Throwable {
        String className = pjp.getTarget().getClass().getSimpleName();
        String methodName = pjp.getSignature().getName();
        Timer.Sample sample = Timer.start(registry);
        try {
            return pjp.proceed();
        } finally {
            sample.stop(Timer.builder("oaas_method_latency_seconds")
                .tag("class", className).tag("method", methodName).register(registry));
        }
    }
}
