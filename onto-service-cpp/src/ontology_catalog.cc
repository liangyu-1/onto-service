#include "onto/service/ontology_catalog.h"

#include <memory>
#include <vector>
#include <map>
#include <string>

#include "googlesql/public/simple_catalog.h"
#include "googlesql/public/simple_property_graph.h"
#include "googlesql/public/simple_table.h"
#include "googlesql/public/type.h"
#include "googlesql/public/types/type_factory.h"
#include "absl/status/status.h"
#include "absl/status/statusor.h"
#include "absl/strings/str_cat.h"

namespace onto {
namespace service {

OntologyCatalog::OntologyCatalog(const std::string& domain_name,
                                  const std::string& version)
    : domain_name_(domain_name), version_(version) {
  catalog_ = std::make_unique<googlesql::SimpleCatalog>(domain_name);
  type_factory_ = std::make_unique<googlesql::TypeFactory>();
}

absl::Status OntologyCatalog::BuildFromTbox(
    const std::vector<std::map<std::string, std::string>>& object_types,
    const std::vector<std::map<std::string, std::string>>& properties,
    const std::vector<std::map<std::string, std::string>>& relationships,
    const std::vector<std::map<std::string, std::string>>& abox_mappings) {
  
  // 1. 创建 PropertyGraph
  std::vector<std::string> name_path = {domain_name_, version_};
  property_graph_ = std::make_unique<googlesql::SimplePropertyGraph>(name_path);

  // 2. 为每个对象类型注册节点表
  for (const auto& obj_type : object_types) {
    auto it = obj_type.find("label_name");
    if (it == obj_type.end()) continue;
    const std::string& label_name = it->second;

    // 收集该类型的属性
    std::vector<std::map<std::string, std::string>> type_properties;
    for (const auto& prop : properties) {
      auto owner_it = prop.find("owner_label");
      if (owner_it != prop.end() && owner_it->second == label_name) {
        type_properties.push_back(prop);
      }
    }

    // 查找 ABOX 映射
    std::map<std::string, std::string> mapping;
    for (const auto& m : abox_mappings) {
      auto class_it = m.find("class_name");
      if (class_it != m.end() && class_it->second == label_name) {
        mapping = m;
        break;
      }
    }

    auto status = RegisterNodeTable(label_name, type_properties, mapping);
    if (!status.ok()) {
      return status;
    }
  }

  // 3. 注册边表 (关系)
  for (const auto& rel : relationships) {
    auto label_it = rel.find("label_name");
    auto source_it = rel.find("source_label");
    auto target_it = rel.find("target_label");
    if (label_it == rel.end() || source_it == rel.end() || target_it == rel.end()) {
      continue;
    }

    auto status = RegisterEdgeTable(
        label_it->second, source_it->second, target_it->second, rel);
    if (!status.ok()) {
      return status;
    }
  }

  // 4. 将 PropertyGraph 注册到 Catalog
  catalog_->AddPropertyGraph(std::move(property_graph_));

  return absl::OkStatus();
}

absl::Status OntologyCatalog::RegisterNodeTable(
    const std::string& label_name,
    const std::vector<std::map<std::string, std::string>>& properties,
    const std::map<std::string, std::string>& abox_mapping) {
  
  // 获取 ABOX 源表名
  std::string source_name = label_name;
  auto it = abox_mapping.find("object_source_name");
  if (it != abox_mapping.end()) {
    source_name = it->second;
  }

  // 创建 SimpleTable 表示 ABOX 数据源
  auto table_or = CreateAboxTable(source_name, properties);
  if (!table_or.ok()) {
    return table_or.status();
  }

  auto table = std::move(table_or.value());
  const googlesql::Table* table_ptr = table.get();

  // 保存 table 到 catalog
  catalog_->AddTable(std::move(table));

  // 创建 GraphElementLabel
  std::vector<std::string> graph_name_path = {domain_name_, version_};
  std::vector<std::unique_ptr<const googlesql::GraphPropertyDeclaration>> prop_decls;
  std::vector<std::unique_ptr<const googlesql::GraphPropertyDefinition>> prop_defs;

  for (const auto& prop : properties) {
    auto name_it = prop.find("property_name");
    auto type_it = prop.find("value_type");
    if (name_it == prop.end()) continue;

    const googlesql::Type* prop_type = type_factory_->get_string();
    if (type_it != prop.end()) {
      if (type_it->second == "DOUBLE" || type_it->second == "FLOAT") {
        prop_type = type_factory_->get_double();
      } else if (type_it->second == "INT64" || type_it->second == "INT") {
        prop_type = type_factory_->get_int64();
      } else if (type_it->second == "BOOL" || type_it->second == "BOOLEAN") {
        prop_type = type_factory_->get_bool();
      }
      // 默认 STRING
    }

    auto prop_decl = std::make_unique<googlesql::SimpleGraphPropertyDeclaration>(
        name_it->second, graph_name_path, prop_type,
        /*type_annotation_map=*/nullptr,
        googlesql::GraphPropertyDeclaration::Kind::kScalar);

    auto col_it = prop.find("column_name");
    std::string expr_sql = col_it != prop.end() ? col_it->second : name_it->second;

    auto prop_def = std::make_unique<googlesql::SimpleGraphPropertyDefinition>(
        prop_decl.get(), expr_sql);

    prop_decls.push_back(std::move(prop_decl));
    prop_defs.push_back(std::move(prop_def));
  }

  // 创建 Label
  std::vector<const googlesql::GraphPropertyDeclaration*> decl_ptrs;
  for (const auto& decl : prop_decls) {
    decl_ptrs.push_back(decl.get());
  }

  auto label = std::make_unique<googlesql::SimpleGraphElementLabel>(
      label_name, graph_name_path, decl_ptrs);

  // 创建 NodeTable
  std::vector<int> key_cols = {0};  // 默认第一列为主键
  auto primary_key_it = abox_mapping.find("primary_key");
  if (primary_key_it != abox_mapping.end()) {
    // TODO: 根据 primary_key 找到对应的列索引
  }

  std::vector<const googlesql::GraphElementLabel*> labels = {label.get()};

  auto node_table = std::make_unique<googlesql::SimpleGraphNodeTable>(
      label_name, graph_name_path, table_ptr, key_cols, labels,
      std::move(prop_defs));

  // 添加到 PropertyGraph
  property_graph_->AddLabel(std::move(label));
  property_graph_->AddNodeTable(std::move(node_table));

  // 保存 property declarations
  for (auto& decl : prop_decls) {
    property_graph_->AddPropertyDeclaration(std::move(decl));
  }

  return absl::OkStatus();
}

absl::Status OntologyCatalog::RegisterEdgeTable(
    const std::string& label_name,
    const std::string& source_label,
    const std::string& target_label,
    const std::map<std::string, std::string>& relationship_def) {
  
  // TODO: 实现边表注册
  // 需要查找 source 和 target 的 NodeTable，创建 GraphNodeTableReference
  return absl::OkStatus();
}

absl::Status OntologyCatalog::Refresh() {
  // 清除现有 catalog 并重建
  catalog_ = std::make_unique<googlesql::SimpleCatalog>(domain_name_);
  property_graph_ = nullptr;
  return absl::OkStatus();
}

absl::StatusOr<std::unique_ptr<googlesql::SimpleTable>>
OntologyCatalog::CreateAboxTable(
    const std::string& table_name,
    const std::vector<std::map<std::string, std::string>>& columns) {
  
  auto table = std::make_unique<googlesql::SimpleTable>(table_name);

  for (const auto& col : columns) {
    auto name_it = col.find("property_name");
    auto type_it = col.find("value_type");
    if (name_it == col.end()) continue;

    const googlesql::Type* col_type = type_factory_->get_string();
    if (type_it != col.end()) {
      if (type_it->second == "DOUBLE" || type_it->second == "FLOAT") {
        col_type = type_factory_->get_double();
      } else if (type_it->second == "INT64" || type_it->second == "INT") {
        col_type = type_factory_->get_int64();
      } else if (type_it->second == "BOOL" || type_it->second == "BOOLEAN") {
        col_type = type_factory_->get_bool();
      }
    }

    table->AddColumn(
        std::make_unique<googlesql::SimpleColumn>(
            table_name, name_it->second, col_type));
  }

  return table;
}

}  // namespace service
}  // namespace onto
