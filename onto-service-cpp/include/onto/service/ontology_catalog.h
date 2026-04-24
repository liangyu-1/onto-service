#ifndef ONTO_SERVICE_ONTOLOGY_CATALOG_H_
#define ONTO_SERVICE_ONTOLOGY_CATALOG_H_

#include <memory>
#include <string>
#include <vector>
#include <map>

#include "googlesql/public/simple_catalog.h"
#include "googlesql/public/simple_property_graph.h"

namespace onto {
namespace service {

/**
 * OntologyCatalog 扩展 SimpleCatalog
 * 
 * 基于 TBOX 元数据动态构建 GoogleSQL Catalog，
 * 包含 PropertyGraph 注册和语义类型映射。
 */
class OntologyCatalog {
 public:
  OntologyCatalog(const std::string& domain_name, const std::string& version);
  ~OntologyCatalog() = default;

  /**
   * 从 TBOX 元数据构建 Catalog
   */
  absl::Status BuildFromTbox(
      const std::vector<std::map<std::string, std::string>>& object_types,
      const std::vector<std::map<std::string, std::string>>& properties,
      const std::vector<std::map<std::string, std::string>>& relationships,
      const std::vector<std::map<std::string, std::string>>& abox_mappings);

  /**
   * 获取构建好的 SimpleCatalog
   */
  googlesql::SimpleCatalog* GetCatalog() { return catalog_.get(); }

  /**
   * 获取 PropertyGraph
   */
  googlesql::SimplePropertyGraph* GetPropertyGraph() { return property_graph_.get(); }

  /**
   * 注册节点表
   */
  absl::Status RegisterNodeTable(
      const std::string& label_name,
      const std::vector<std::map<std::string, std::string>>& properties,
      const std::map<std::string, std::string>& abox_mapping);

  /**
   * 注册边表
   */
  absl::Status RegisterEdgeTable(
      const std::string& label_name,
      const std::string& source_label,
      const std::string& target_label,
      const std::map<std::string, std::string>& relationship_def);

  /**
   * 刷新 Catalog (当 TBOX 变更时)
   */
  absl::Status Refresh();

 private:
  std::string domain_name_;
  std::string version_;
  std::unique_ptr<googlesql::SimpleCatalog> catalog_;
  std::unique_ptr<googlesql::SimplePropertyGraph> property_graph_;
  std::unique_ptr<googlesql::TypeFactory> type_factory_;

  /**
   * 创建 SimpleTable 表示 ABOX 数据源
   */
  absl::StatusOr<std::unique_ptr<googlesql::SimpleTable>> CreateAboxTable(
      const std::string& table_name,
      const std::vector<std::map<std::string, std::string>>& columns);
};

}  // namespace service
}  // namespace onto

#endif  // ONTO_SERVICE_ONTOLOGY_CATALOG_H_
