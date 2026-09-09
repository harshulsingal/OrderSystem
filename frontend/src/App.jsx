import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  Package, 
  Boxes, 
  ShoppingCart, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle, 
  Plus, 
  Activity, 
  Database,
  ArrowRight,
  TrendingUp,
  Cpu
} from 'lucide-react';

const API_BASE = 'http://localhost:8000';

export default function App() {
  const [backendStatus, setBackendStatus] = useState('checking');
  const [products, setProducts] = useState([]);
  const [inventory, setInventory] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  // AI Demo Generation State
  const [demoCount, setDemoCount] = useState(10);
  const [isGenerating, setIsGenerating] = useState(false);
  const [notification, setNotification] = useState(null);

  // Manual Form States
  const [activeTab, setActiveTab] = useState('products');
  const [newProduct, setNewProduct] = useState({ name: '', sku: '', price: '' });
  const [newInventory, setNewInventory] = useState({ product_id: '', available_quantity: '' });
  const [newOrder, setNewOrder] = useState({ user_id: 1, product_id: '', quantity: 1 });

  useEffect(() => {
    checkHealthAndFetchAll();
    const interval = setInterval(checkHealthAndFetchAll, 10000);
    return () => clearInterval(interval);
  }, []);

  const showNotification = (type, message) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 5000);
  };

  const checkHealthAndFetchAll = async () => {
    try {
      const healthRes = await fetch(`${API_BASE}/health/db`);
      if (healthRes.ok) {
        setBackendStatus('connected');
        await Promise.all([fetchProducts(), fetchInventory(), fetchOrders()]);
      } else {
        setBackendStatus('offline');
      }
    } catch {
      setBackendStatus('offline');
    } finally {
      setLoading(false);
    }
  };

  const fetchProducts = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/products`);
      if (res.ok) setProducts(await res.json());
    } catch (e) {
      console.error('Error fetching products:', e);
    }
  };

  const fetchInventory = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/inventory`);
      if (res.ok) setInventory(await res.json());
    } catch (e) {
      console.error('Error fetching inventory:', e);
    }
  };

  const fetchOrders = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/orders`);
      if (res.ok) setOrders(await res.json());
    } catch (e) {
      console.error('Error fetching orders:', e);
    }
  };

  // AI Demo Data Generation
  const handleGenerateDemoData = async (e) => {
    e.preventDefault();
    if (demoCount < 1 || demoCount > 20) {
      showNotification('error', 'Please choose between 1 and 20 products.');
      return;
    }

    setIsGenerating(true);
    try {
      const res = await fetch(`${API_BASE}/api/demo/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ count: Number(demoCount) }),
      });

      if (!res.ok) {
        throw new Error('AI Generation failed');
      }

      const data = await res.json();
      showNotification('success', `${data.count} products generated successfully.`);
      
      // Refresh state without full page reload
      await Promise.all([fetchProducts(), fetchInventory()]);
      setActiveTab('products');
    } catch (error) {
      console.error(error);
      showNotification('error', 'AI data generation failed. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  // Manual Product Creation
  const handleCreateProduct = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/api/products`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newProduct.name,
          sku: newProduct.sku,
          price: parseFloat(newProduct.price),
        }),
      });

      if (res.status === 409) {
        showNotification('error', 'Product with this SKU already exists (409 Conflict).');
        return;
      }

      if (!res.ok) throw new Error('Creation failed');

      const created = await res.json();
      showNotification('success', `Product "${created.name}" created!`);
      setNewProduct({ name: '', sku: '', price: '' });
      await fetchProducts();
    } catch {
      showNotification('error', 'Failed to create product.');
    }
  };

  // Manual Inventory Creation
  const handleCreateInventory = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/api/inventory`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_id: parseInt(newInventory.product_id),
          available_quantity: parseInt(newInventory.available_quantity),
        }),
      });

      if (res.status === 409) {
        showNotification('error', 'Inventory for this product already exists (409).');
        return;
      }
      if (res.status === 404) {
        showNotification('error', 'Product ID not found (404).');
        return;
      }
      if (!res.ok) throw new Error('Creation failed');

      showNotification('success', 'Inventory added successfully!');
      setNewInventory({ product_id: '', available_quantity: '' });
      await fetchInventory();
    } catch {
      showNotification('error', 'Failed to create inventory record.');
    }
  };

  // Manual Order Creation
  const handleCreateOrder = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/api/orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: parseInt(newOrder.user_id),
          items: [{
            product_id: parseInt(newOrder.product_id),
            quantity: parseInt(newOrder.quantity),
          }],
        }),
      });

      if (res.status === 404) {
        showNotification('error', 'Product ID not found in database.');
        return;
      }
      if (!res.ok) throw new Error('Creation failed');

      const created = await res.json();
      showNotification('success', `Order #${created.id} created for ₹${created.total_amount}!`);
      setNewOrder({ user_id: 1, product_id: '', quantity: 1 });
      await fetchOrders();
      setActiveTab('orders');
    } catch {
      showNotification('error', 'Failed to place order.');
    }
  };

  // Inventory lookup helper
  const inventoryMap = {};
  inventory.forEach(inv => {
    inventoryMap[inv.product_id] = inv;
  });

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '32px 24px' }}>
      
      {/* Top Navigation / Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ background: 'var(--accent-primary)', width: '38px', height: '38px', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Boxes color="#fff" size={22} />
            </div>
            <div>
              <h1 style={{ fontSize: '1.5rem', fontWeight: '800', letterSpacing: '-0.02em' }}>OrderSystem</h1>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Distributed Order & Inventory Backend Platform</p>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* Backend Status Indicator */}
          <div className="glass-panel" style={{ padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '10px', borderRadius: '9999px' }}>
            <span style={{ 
              width: '8px', 
              height: '8px', 
              borderRadius: '50%', 
              backgroundColor: backendStatus === 'connected' ? '#10b981' : '#ef4444',
              boxShadow: backendStatus === 'connected' ? '0 0 10px #10b981' : '0 0 10px #ef4444'
            }} />
            <span style={{ fontSize: '0.8rem', fontWeight: '600', color: backendStatus === 'connected' ? '#34d399' : '#f87171' }}>
              {backendStatus === 'connected' ? 'PostgreSQL Connected' : 'Backend Offline'}
            </span>
          </div>

          <button 
            className="btn btn-secondary"
            onClick={checkHealthAndFetchAll}
            disabled={loading || isGenerating}
            title="Refresh dashboard data"
          >
            <RefreshCw size={15} className={loading ? 'spin' : ''} />
            Refresh
          </button>
        </div>
      </header>

      {/* Notification Toast */}
      {notification && (
        <div style={{
          marginBottom: '24px',
          padding: '14px 20px',
          borderRadius: 'var(--radius-md)',
          background: notification.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
          border: `1px solid ${notification.type === 'success' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
          color: notification.type === 'success' ? '#34d399' : '#f87171',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontWeight: '500',
          fontSize: '0.9rem'
        }}>
          {notification.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          {notification.message}
        </div>
      )}

      {/* Grid: AI Demo Generator + Manual Controls */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px', marginBottom: '36px' }}>
        
        {/* AI Demo Generation Card */}
        <div className={`glass-panel ai-card ${isGenerating ? 'pulsing-ai' : ''}`} style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sparkles size={20} color="#06b6d4" />
              <span style={{ fontSize: '0.75rem', fontWeight: '800', color: '#06b6d4', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                AI Data Generation
              </span>
            </div>
            <span className="badge badge-info">OpenAI Powered</span>
          </div>

          <h3 style={{ fontSize: '1.15rem', fontWeight: '700', marginBottom: '6px' }}>
            Generate Realistic Demo Catalog
          </h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '20px' }}>
            Uses OpenAI to generate realistic demo products and inventory.
          </p>

          <form onSubmit={handleGenerateDemoData} style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: '500' }}>Count:</label>
              <input 
                type="number" 
                min="1" 
                max="20" 
                value={demoCount}
                onChange={(e) => setDemoCount(Math.max(1, Math.min(20, parseInt(e.target.value) || 1)))}
                disabled={isGenerating}
                className="input-field mono"
                style={{ width: '70px', textAlign: 'center', padding: '8px 10px' }}
              />
            </div>

            <button 
              type="submit" 
              className="btn btn-ai"
              disabled={isGenerating || backendStatus !== 'connected'}
              style={{ flex: 1, minWidth: '180px' }}
            >
              <Sparkles size={16} />
              {isGenerating ? 'Generating demo data with AI...' : '✨ Generate Demo Data'}
            </button>
          </form>

          {isGenerating && (
            <div style={{ marginTop: '14px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.82rem', color: '#38bdf8' }}>
              <Cpu size={14} className="spin" />
              Calling OpenAI API, validating candidate items, and committing to PostgreSQL...
            </div>
          )}
        </div>

        {/* Quick Metrics */}
        <div className="glass-panel" style={{ padding: '24px', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', alignItems: 'center' }}>
          <div style={{ textAlign: 'center', borderRight: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '8px' }}>
              <Package size={20} color="#6366f1" />
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: '800' }}>{products.length}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Products</div>
          </div>

          <div style={{ textAlign: 'center', borderRight: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '8px' }}>
              <Boxes size={20} color="#10b981" />
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: '800' }}>{inventory.length}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Stock Tracks</div>
          </div>

          <div style={{ textAlign: 'center' }}>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '8px' }}>
              <ShoppingCart size={20} color="#f59e0b" />
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: '800' }}>{orders.length}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Orders</div>
          </div>
        </div>

      </div>

      {/* Navigation Tabs */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px', marginBottom: '24px' }}>
        {[
          { id: 'products', label: 'Products Catalog', icon: Package, count: products.length },
          { id: 'inventory', label: 'Inventory Stocks', icon: Boxes, count: inventory.length },
          { id: 'orders', label: 'Orders Placed', icon: ShoppingCart, count: orders.length },
          { id: 'manual', label: 'Manual Creation Forms', icon: Plus },
        ].map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="btn"
              style={{
                background: isActive ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
                color: isActive ? '#818cf8' : 'var(--text-secondary)',
                border: isActive ? '1px solid rgba(99, 102, 241, 0.3)' : '1px solid transparent',
              }}
            >
              <Icon size={16} />
              {tab.label}
              {tab.count !== undefined && (
                <span className="mono" style={{ background: 'rgba(255, 255, 255, 0.08)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.75rem' }}>
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab: Products */}
      {activeTab === 'products' && (
        <div className="glass-panel" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: '1rem', fontWeight: '700' }}>Products List ({products.length})</h2>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Backed by PostgreSQL `products` table</span>
          </div>

          {products.length === 0 ? (
            <div style={{ padding: '48px 24px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <Package size={40} style={{ margin: '0 auto 12px', opacity: 0.4 }} />
              <p>No products found in the catalog.</p>
              <p style={{ fontSize: '0.85rem', marginTop: '4px' }}>Click "✨ Generate Demo Data" above to quickly populate the database.</p>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Product Name</th>
                    <th>SKU</th>
                    <th>Price (INR)</th>
                    <th>Available Stock</th>
                    <th>Created At</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map(p => {
                    const inv = inventoryMap[p.id];
                    return (
                      <tr key={p.id}>
                        <td className="mono" style={{ color: 'var(--text-muted)' }}>#{p.id}</td>
                        <td style={{ fontWeight: '600', color: 'var(--text-primary)' }}>{p.name}</td>
                        <td><span className="mono badge badge-info">{p.sku}</span></td>
                        <td className="mono" style={{ fontWeight: '600', color: '#34d399' }}>₹{Number(p.price).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                        <td>
                          {inv ? (
                            <span className={`badge ${inv.available_quantity > 0 ? 'badge-success' : 'badge-danger'}`}>
                              {inv.available_quantity} Units
                            </span>
                          ) : (
                            <span className="badge badge-warning">No Record</span>
                          )}
                        </td>
                        <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                          {new Date(p.created_at).toLocaleString()}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab: Inventory */}
      {activeTab === 'inventory' && (
        <div className="glass-panel" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)' }}>
            <h2 style={{ fontSize: '1rem', fontWeight: '700' }}>Inventory Stock Table ({inventory.length})</h2>
          </div>

          {inventory.length === 0 ? (
            <div style={{ padding: '48px 24px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <Boxes size={40} style={{ margin: '0 auto 12px', opacity: 0.4 }} />
              <p>No inventory records found.</p>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Inv ID</th>
                    <th>Product ID</th>
                    <th>Available Quantity</th>
                    <th>Reserved Quantity</th>
                    <th>Created At</th>
                    <th>Updated At</th>
                  </tr>
                </thead>
                <tbody>
                  {inventory.map(inv => (
                    <tr key={inv.id}>
                      <td className="mono" style={{ color: 'var(--text-muted)' }}>#{inv.id}</td>
                      <td className="mono" style={{ fontWeight: '600' }}>Product #{inv.product_id}</td>
                      <td>
                        <span className="badge badge-success mono">{inv.available_quantity} available</span>
                      </td>
                      <td>
                        <span className="badge badge-warning mono">{inv.reserved_quantity} reserved</span>
                      </td>
                      <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{new Date(inv.created_at).toLocaleTimeString()}</td>
                      <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{new Date(inv.updated_at).toLocaleTimeString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab: Orders */}
      {activeTab === 'orders' && (
        <div className="glass-panel" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)' }}>
            <h2 style={{ fontSize: '1rem', fontWeight: '700' }}>Customer Orders ({orders.length})</h2>
          </div>

          {orders.length === 0 ? (
            <div style={{ padding: '48px 24px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <ShoppingCart size={40} style={{ margin: '0 auto 12px', opacity: 0.4 }} />
              <p>No orders created yet.</p>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Order ID</th>
                    <th>User ID</th>
                    <th>Status</th>
                    <th>Total Amount</th>
                    <th>Items Purchased</th>
                    <th>Created At</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map(order => (
                    <tr key={order.id}>
                      <td className="mono" style={{ fontWeight: '700' }}>#{order.id}</td>
                      <td className="mono">User #{order.user_id}</td>
                      <td><span className="badge badge-warning">{order.status}</span></td>
                      <td className="mono" style={{ fontWeight: '600', color: '#34d399' }}>₹{Number(order.total_amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          {order.items?.map(item => (
                            <span key={item.id} className="mono" style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                              • Product #{item.product_id} × {item.quantity} (@ ₹{item.price})
                            </span>
                          ))}
                        </div>
                      </td>
                      <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{new Date(order.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab: Manual Creation Forms */}
      {activeTab === 'manual' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px' }}>
          
          {/* Create Product Form */}
          <div className="glass-panel" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: '700', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Package size={18} color="#6366f1" /> Create Product Manually
            </h3>
            <form onSubmit={handleCreateProduct} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Product Name</label>
                <input 
                  type="text" 
                  className="input-field" 
                  placeholder="e.g. Sony WH-1000XM5" 
                  value={newProduct.name}
                  onChange={e => setNewProduct({...newProduct, name: e.target.value})}
                  required 
                />
              </div>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>SKU (Unique)</label>
                <input 
                  type="text" 
                  className="input-field mono" 
                  placeholder="e.g. SONY-WH5-BLK" 
                  value={newProduct.sku}
                  onChange={e => setNewProduct({...newProduct, sku: e.target.value})}
                  required 
                />
              </div>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Price (INR)</label>
                <input 
                  type="number" 
                  step="0.01" 
                  min="0.01"
                  className="input-field mono" 
                  placeholder="29990.00" 
                  value={newProduct.price}
                  onChange={e => setNewProduct({...newProduct, price: e.target.value})}
                  required 
                />
              </div>
              <button type="submit" className="btn btn-primary" style={{ marginTop: '8px' }}>
                <Plus size={16} /> Add Product
              </button>
            </form>
          </div>

          {/* Create Inventory Form */}
          <div className="glass-panel" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: '700', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Boxes size={18} color="#10b981" /> Set Product Inventory
            </h3>
            <form onSubmit={handleCreateInventory} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Product ID</label>
                <input 
                  type="number" 
                  className="input-field mono" 
                  placeholder="e.g. 1" 
                  value={newInventory.product_id}
                  onChange={e => setNewInventory({...newInventory, product_id: e.target.value})}
                  required 
                />
              </div>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Available Quantity</label>
                <input 
                  type="number" 
                  min="0"
                  className="input-field mono" 
                  placeholder="50" 
                  value={newInventory.available_quantity}
                  onChange={e => setNewInventory({...newInventory, available_quantity: e.target.value})}
                  required 
                />
              </div>
              <button type="submit" className="btn btn-primary" style={{ marginTop: 'auto' }}>
                <Plus size={16} /> Save Inventory
              </button>
            </form>
          </div>

          {/* Create Order Form */}
          <div className="glass-panel" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: '700', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShoppingCart size={18} color="#f59e0b" /> Place New Order
            </h3>
            <form onSubmit={handleCreateOrder} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Customer User ID</label>
                <input 
                  type="number" 
                  className="input-field mono" 
                  placeholder="1" 
                  value={newOrder.user_id}
                  onChange={e => setNewOrder({...newOrder, user_id: e.target.value})}
                  required 
                />
              </div>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Product ID to Purchase</label>
                <input 
                  type="number" 
                  className="input-field mono" 
                  placeholder="e.g. 1" 
                  value={newOrder.product_id}
                  onChange={e => setNewOrder({...newOrder, product_id: e.target.value})}
                  required 
                />
              </div>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Quantity</label>
                <input 
                  type="number" 
                  min="1"
                  className="input-field mono" 
                  placeholder="1" 
                  value={newOrder.quantity}
                  onChange={e => setNewOrder({...newOrder, quantity: e.target.value})}
                  required 
                />
              </div>
              <button type="submit" className="btn btn-primary" style={{ marginTop: '8px' }}>
                <ArrowRight size={16} /> Place Order
              </button>
            </form>
          </div>

        </div>
      )}

    </div>
  );
}
