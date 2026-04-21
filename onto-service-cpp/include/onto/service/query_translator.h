#ifndef ONTO_SERVICE_QUERY_TRANSLATOR_H_
#define ONTO_SERVICE_QUERY_TRANSLATOR_H_

#include <memory>
#include <string>
#include <vector>
#include <map>

#include "googlesql/resolved_ast/resolved_ast.h"

namespace onto {
namespace service {

class OntologyCatalog;

/**
 * QueryTranslator
 * 
 * 将 Resolved AST 转换为 Doris 可执行的 SQL。
 * 处理语义层到物理层的映射转换。
 */
class QueryTranslator {
 public:
  QueryTranslator(OntologyCatalog* catalog);
  ~QueryTranslator() = default;

  /**
   * 将 Resolved AST 转换为 Doris SQL
   */
  absl::StatusOr<std::string> TranslateToDorisSql(
      const googlesql::ResolvedNode* resolved_ast);

  /**
   * 处理 Property Graph MATCH 语句
   */
  absl::StatusOr<std::string> TranslateGraphMatch(
      const googlesql::ResolvedNode* match_stmt);

  /**
   * 处理语义属性到物理列的映射
   */
  absl::StatusOr<std::string> ResolvePropertyProjection(
      const std::string& semantic_property,
      const std::string& object_type);

  /**
   * 处理关系导航 (ROW/MULTIROW 伪列)
   */
  absl::StatusOr<std::string> ResolveRelationshipNavigation(
      const std::string& source_type,
      const std::string& navigation_name);

  /**
   * 生成带物化视图提示的 SQL
   */
  absl::StatusOr<std::string> GenerateSqlWithMvHint(
      const std::string& base_sql,
      const std::vector<std::string>& mv_candidates);

 private:
  OntologyCatalog* catalog_;

  /**
   * 处理 ResolvedScan 节点
   */
  absl::StatusOr<std::string> TranslateScan(
      const googlesql::ResolvedScan* scan);

  /**
   * 处理 ResolvedExpr 节点
   */
  absl::StatusOr<std::string> TranslateExpr(
      const googlesql::ResolvedExpr* expr);

  /**
   * 处理 JOIN
   */
  absl::StatusOr<std::string> TranslateJoin(
      const googlesql::ResolvedJoinScan* join_scan);
};

}  // namespace service
}  // namespace onto

#endif  // ONTO_SERVICE_QUERY_TRANSLATOR_H_
