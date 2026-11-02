class AddStatusToOrders < ActiveRecord::Migration[7.1]
  def change
    add_column :orders, :status, :string, null: false
    add_index :orders, :status
    rename_column :orders, :total, :total_cents
    add_foreign_key :orders, :users
    Order.update_all(status: "new")
  end
end
