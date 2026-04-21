#include "onto/service/ontology_analyzer.h"

#include <memory>
#include <string>
#include <vector>

#include "googlesql/public/analyzer.h"
#include "googlesql/public/analyzer_options.h"
#include "googlesql/public/analyzer_output.h"
#include "googlesql/public/simple_catalog.h"
#include "googlesql/resolved_ast/resolved_ast.h"
#include "googlesql/resolved_ast/resolved_node.h"
#include "absl/status/status.h"
#include "absl/status/statusor.h"
#include "absl/strings/str_cat.h"

namespace onto {
namespace service {

OntologyAnalyzer::OntologyAnalyzer(OntologyCatalog* catalog)
    : catalog_(catalog) {
  InitializeAnalyzerOptions();
  analyzer_ = std::make_unique<googlesql::Analyzer>(analyzer_options_, catalog_->GetCatalog());
}

void OntologyAnalyzer::InitializeAnalyzerOptions() {
  analyzer_options_.set_language_options(
      googlesql::AnalyzerOptions::kLanguageVersionCurrent);
  
  // 启用 Property Graph 支持
  analyzer_options_.mutable_language_options()->
      EnableMaximumLanguageFeaturesForDevelopment();
}

absl::StatusOr<std::unique_ptr<const googlesql::AnalyzerOutput>>
OntologyAnalyzer::AnalyzeSql(const std::string& sql) {
  std::unique_ptr<const googlesql::AnalyzerOutput> output;
  
  auto status = googlesql::AnalyzeStatement(
      sql, analyzer_options_, catalog_->GetCatalog(),
      catalog_->GetCatalog()->GetTypeFactory(), &output);
  
  if (!status.ok()) {
    return status;
  }
  
  return std::move(output);
}

absl::StatusOr<std::unique_ptr<const googlesql::AnalyzerOutput>>
OntologyAnalyzer::AnalyzeGraphQuery(
    const std::string& match_pattern,
    const std::string& where_clause,
    const std::string& return_clause) {
  
  // 构建完整的 MATCH 语句
  std::string sql = absl::StrCat(
      "SELECT ", return_clause,
      " FROM GRAPH ", catalog_->GetCatalog()->FullName(),
      " MATCH ", match_pattern);
  
  if (!where_clause.empty()) {
    absl::StrAppend(&sql, " WHERE ", where_clause);
  }

  return AnalyzeSql(sql);
}

const googlesql::ResolvedNode* OntologyAnalyzer::GetResolvedAst(
    const googlesql::AnalyzerOutput& output) {
  return output.resolved_statement();
}

absl::Status OntologyAnalyzer::ValidateQueryAccess(
    const googlesql::AnalyzerOutput& output,
    const std::vector<std::string>& allowed_sources) {
  
  // TODO: 遍历 Resolved AST，验证只访问了允许的表/视图
  // 可以使用 ResolvedASTVisitor 遍历所有 ResolvedScan 节点
  
  return absl::OkStatus();
}

}  // namespace service
}  // namespace onto
