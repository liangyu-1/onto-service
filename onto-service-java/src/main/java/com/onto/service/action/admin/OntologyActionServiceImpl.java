package com.onto.service.action.admin;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.onto.service.entity.OntologyAction;
import com.onto.service.entity.OntologyActionBinding;
import com.onto.service.mapper.OntologyActionMapper;
import com.onto.service.mapper.OntologyActionBindingMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * Action 管理服务实现
 */
@Service
public class OntologyActionServiceImpl implements OntologyActionService {

    @Autowired
    private OntologyActionMapper actionMapper;

    @Autowired
    private OntologyActionBindingMapper actionBindingMapper;

    @Override
    public OntologyAction createAction(OntologyAction action) {
        actionMapper.insert(action);
        return action;
    }

    @Override
    public List<OntologyAction> listActions(String domainName, String version) {
        QueryWrapper<OntologyAction> wrapper = new QueryWrapper<>();
        wrapper.eq("domain_name", domainName).eq("version", version);
        return actionMapper.selectList(wrapper);
    }

    @Override
    public OntologyAction getAction(String domainName, String version, String actionName) {
        QueryWrapper<OntologyAction> wrapper = new QueryWrapper<>();
        wrapper.eq("domain_name", domainName)
               .eq("version", version)
               .eq("action_name", actionName);
        return actionMapper.selectOne(wrapper);
    }

    @Override
    public OntologyAction updateAction(OntologyAction action) {
        UpdateWrapper<OntologyAction> wrapper = new UpdateWrapper<>();
        wrapper.eq("domain_name", action.getDomainName())
               .eq("version", action.getVersion())
               .eq("action_name", action.getActionName());
        actionMapper.update(action, wrapper);
        return action;
    }

    @Override
    public void deleteAction(String domainName, String version, String actionName) {
        QueryWrapper<OntologyAction> wrapper = new QueryWrapper<>();
        wrapper.eq("domain_name", domainName)
               .eq("version", version)
               .eq("action_name", actionName);
        actionMapper.delete(wrapper);
    }

    @Override
    public OntologyActionBinding createBinding(OntologyActionBinding binding) {
        actionBindingMapper.insert(binding);
        return binding;
    }

    @Override
    public List<OntologyActionBinding> listBindings(String domainName, String version) {
        QueryWrapper<OntologyActionBinding> wrapper = new QueryWrapper<>();
        wrapper.eq("domain_name", domainName).eq("version", version);
        return actionBindingMapper.selectList(wrapper);
    }

    @Override
    public OntologyActionBinding getBinding(String domainName, String version, String actionName, String platformName) {
        QueryWrapper<OntologyActionBinding> wrapper = new QueryWrapper<>();
        wrapper.eq("domain_name", domainName)
               .eq("version", version)
               .eq("action_name", actionName)
               .eq("platform_name", platformName);
        return actionBindingMapper.selectOne(wrapper);
    }

    @Override
    public OntologyActionBinding updateBinding(OntologyActionBinding binding) {
        UpdateWrapper<OntologyActionBinding> wrapper = new UpdateWrapper<>();
        wrapper.eq("domain_name", binding.getDomainName())
               .eq("version", binding.getVersion())
               .eq("action_name", binding.getActionName())
               .eq("platform_name", binding.getPlatformName());
        actionBindingMapper.update(binding, wrapper);
        return binding;
    }

    @Override
    public void deleteBinding(String domainName, String version, String actionName, String platformName) {
        QueryWrapper<OntologyActionBinding> wrapper = new QueryWrapper<>();
        wrapper.eq("domain_name", domainName)
               .eq("version", version)
               .eq("action_name", actionName)
               .eq("platform_name", platformName);
        actionBindingMapper.delete(wrapper);
    }
}
