class AddStatusToOrders < ActiveRecord::Migration[7.1]
  disable_ddl_transaction!
  def change
    add_column :orders, :status, :string
    add_index :orders, :status, algorithm: :concurrently
    add_foreign_key :orders, :users, validate: false
  end
end
