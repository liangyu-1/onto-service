#ifndef ONTO_SERVICE_ONTOLOGY_ANALYZER_H_
#define ONTO_SERVICE_ONTOLOGY_ANALYZER_H_

#include <memory>
#include <string>

#include "googlesql/public/analyzer.h"
#include "googlesql/public/analyzer_options.h"
#include "googlesql/resolved_ast/resolved_ast.h"

namespace onto {
namespace service {

class OntologyCatalog;

/**
 * OntologyAnalyzer
 * 
 * 封装 GoogleSQL Analyzer，提供语义 SQL 分析能力。
 * 支持 Property Graph MATCH 语句和常规 SQL 的分析。
 */
class OntologyAnalyzer {
 public:
  OntologyAnalyzer(OntologyCatalog* catalog);
  ~OntologyAnalyzer() = default;

  /**
   * 分析 SQL 语句
   */
  absl::StatusOr<std::unique_ptr<const googlesql::AnalyzerOutput>> AnalyzeSql(
      const std::string& sql);

  /**
   * 分析 Graph MATCH 语句
   */
  absl::StatusOr<std::unique_ptr<const googlesql::AnalyzerOutput>> AnalyzeGraphQuery(
      const std::string& match_pattern,
      const std::string& where_clause,
      const std::string& return_clause);

  /**
   * 获取 Resolved AST
   */
  const googlesql::ResolvedNode* GetResolvedAst(
      const googlesql::AnalyzerOutput& output);

  /**
   * 验证查询是否只访问允许的表/视图
   */
  absl::Status ValidateQueryAccess(
      const googlesql::AnalyzerOutput& output,
      const std::vector<std::string>& allowed_sources);

 private:
  OntologyCatalog* catalog_;
  googlesql::AnalyzerOptions analyzer_options_;
  std::unique_ptr<googlesql::Analyzer> analyzer_;

  void InitializeAnalyzerOptions();
};

}  // namespace service
}  // namespace onto

#endif  // ONTO_SERVICE_ONTOLOGY_ANALYZER_H_
