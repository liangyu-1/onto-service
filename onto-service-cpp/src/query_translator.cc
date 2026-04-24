#include "onto/service/query_translator.h"

#include <memory>
#include <string>
#include <vector>
#include <map>

#include "googlesql/resolved_ast/resolved_ast.h"
#include "googlesql/resolved_ast/resolved_node.h"
#include "googlesql/resolved_ast/resolved_ast_enums.pb.h"
#include "absl/status/status.h"
#include "absl/status/statusor.h"
#include "absl/strings/str_cat.h"
#include "absl/strings/str_join.h"

namespace onto {
namespace service {

QueryTranslator::QueryTranslator(OntologyCatalog* catalog)
    : catalog_(catalog) {}

absl::StatusOr<std::string> QueryTranslator::TranslateToDorisSql(
    const googlesql::ResolvedNode* resolved_ast) {
  
  if (resolved_ast == nullptr) {
    return absl::InvalidArgumentError("Resolved AST is null");
  }

  // 根据节点类型进行转换
  switch (resolved_ast->node_kind()) {
    case googlesql::RESOLVED_QUERY_STMT: {
      // 处理查询语句
      auto* query_stmt = resolved_ast->GetAs<googlesql::ResolvedQueryStmt>();
      return TranslateScan(query_stmt->query()->query_scan());
    }
    case googlesql::RESOLVED_GRAPH_TABLE_SCAN: {
      // 处理 GRAPH TABLE 扫描
      return TranslateGraphMatch(resolved_ast);
    }
    default:
      return absl::UnimplementedError(
          absl::StrCat("Unsupported node kind: ", resolved_ast->node_kind()));
  }
}

absl::StatusOr<std::string> QueryTranslator::TranslateGraphMatch(
    const googlesql::ResolvedNode* match_stmt) {
  
  // TODO: 将 Graph MATCH 转换为 Doris SQL
  // 1. 解析 MATCH 模式
  // 2. 将节点映射到 ABOX 表
  // 3. 将边映射到 JOIN 条件
  // 4. 生成标准 SQL

  std::string sql = "-- Translated from Property Graph MATCH\n";
  absl::StrAppend(&sql, "SELECT * FROM (\n");
  absl::StrAppend(&sql, "  -- TODO: Implement graph match translation\n");
  absl::StrAppend(&sql, ")");

  return sql;
}

absl::StatusOr<std::string> QueryTranslator::ResolvePropertyProjection(
    const std::string& semantic_property,
    const std::string& object_type) {
  
  // TODO: 查询 ontology_property 表，获取属性到物理列的映射
  // 返回物理列名或表达式

  return semantic_property;  // 默认直接返回
}

absl::StatusOr<std::string> QueryTranslator::ResolveRelationshipNavigation(
    const std::string& source_type,
    const std::string& navigation_name) {
  
  // TODO: 查询 ontology_relationship 表
  // 根据 outgoing_name 或 incoming_name 找到对应的关系定义
  // 生成 JOIN SQL

  return absl::StrCat("-- Navigation: ", source_type, ".", navigation_name);
}

absl::StatusOr<std::string> QueryTranslator::GenerateSqlWithMvHint(
    const std::string& base_sql,
    const std::vector<std::string>& mv_candidates) {
  
  // Doris 支持物化视图查询重写，通常不需要显式提示
  // 这里可以添加注释或优化器提示

  std::string sql = base_sql;
  if (!mv_candidates.empty()) {
    absl::StrAppend(&sql, "\n-- MV candidates: ", absl::StrJoin(mv_candidates, ", "));
  }
  return sql;
}

absl::StatusOr<std::string> QueryTranslator::TranslateScan(
    const googlesql::ResolvedScan* scan) {
  
  if (scan == nullptr) {
    return "SELECT 1";
  }

  switch (scan->node_kind()) {
    case googlesql::RESOLVED_TABLE_SCAN: {
      auto* table_scan = scan->GetAs<googlesql::ResolvedTableScan>();
      return absl::StrCat("SELECT * FROM ", table_scan->table()->Name());
    }
    case googlesql::RESOLVED_JOIN_SCAN: {
      return TranslateJoin(scan->GetAs<googlesql::ResolvedJoinScan>());
    }
    case googlesql::RESOLVED_PROJECT_SCAN: {
      auto* project_scan = scan->GetAs<googlesql::ResolvedProjectScan>();
      auto input_or = TranslateScan(project_scan->input_scan());
      if (!input_or.ok()) return input_or;
      // TODO: 处理列投影
      return input_or;
    }
    default:
      return absl::StrCat("-- Unsupported scan: ", scan->node_kind());
  }
}

absl::StatusOr<std::string> QueryTranslator::TranslateExpr(
    const googlesql::ResolvedExpr* expr) {
  
  if (expr == nullptr) {
    return "";
  }

  // TODO: 实现表达式转换
  return "-- expr";
}

absl::StatusOr<std::string> QueryTranslator::TranslateJoin(
    const googlesql::ResolvedJoinScan* join_scan) {
  
  if (join_scan == nullptr) {
    return "";
  }

  auto left_or = TranslateScan(join_scan->left_scan());
  auto right_or = TranslateScan(join_scan->right_scan());

  if (!left_or.ok()) return left_or;
  if (!right_or.ok()) return right_or;

  std::string join_type = "INNER JOIN";
  switch (join_scan->join_type()) {
    case googlesql::ResolvedJoinScan::INNER:
      join_type = "INNER JOIN";
      break;
    case googlesql::ResolvedJoinScan::LEFT:
      join_type = "LEFT JOIN";
      break;
    case googlesql::ResolvedJoinScan::RIGHT:
      join_type = "RIGHT JOIN";
      break;
    case googlesql::ResolvedJoinScan::FULL:
      join_type = "FULL JOIN";
      break;
    default:
      break;
  }

  // TODO: 处理 JOIN 条件
  return absl::StrCat(
      "(", left_or.value(), ") ", join_type,
      " (", right_or.value(), ")",
      " ON -- TODO: join condition");
}

}  // namespace service
}  // namespace onto
