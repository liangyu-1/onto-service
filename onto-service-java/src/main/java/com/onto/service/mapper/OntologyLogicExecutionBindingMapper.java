package com.onto.service.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.onto.service.entity.OntologyLogicExecutionBinding;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * Logic 执行绑定 Mapper
 */
@Mapper
public interface OntologyLogicExecutionBindingMapper extends BaseMapper<OntologyLogicExecutionBinding> {

    @Select("SELECT * FROM ontology_logic_execution_binding WHERE domain_name = #{domainName} AND version = #{version} AND logic_name = #{logicName}")
    List<OntologyLogicExecutionBinding> selectByLogicName(@Param("domainName") String domainName, @Param("version") String version, @Param("logicName") String logicName);
}
