package com.onto.oaas.aop;

import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.stereotype.Component;

@Aspect
@Component
@Slf4j
public class LoggingAspect {
    @Around("@within(org.springframework.web.bind.annotation.RestController)")
    public Object logRequestResponse(ProceedingJoinPoint pjp) throws Throwable {
        String method = pjp.getSignature().toShortString();
        long start = System.currentTimeMillis();
        try {
            Object result = pjp.proceed();
            long cost = System.currentTimeMillis() - start;
            log.info("[API] {} cost={}ms status=OK", method, cost);
            return result;
        } catch (Exception e) {
            long cost = System.currentTimeMillis() - start;
            log.error("[API] {} cost={}ms status=ERROR error={}", method, cost, e.getMessage());
            throw e;
        }
    }
}
