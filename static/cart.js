/**
 * DropHub Unified Cart & Dropdown Engine (cart.js)
 * Manages cart state in localStorage, dynamic rendering of header dropdown,
 * badge counters, toast notifications, quantity updates, and item removal.
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'drophub_cart_v2';

  var DEFAULT_ITEMS = [
    {
      id: 'prod_headphones',
      name: 'Wireless Noise-Cancelling Headphones',
      store: 'TechVault Store',
      price: 89.99,
      img: '/static/img/headphones.jpg',
      qty: 1
    },
    {
      id: 'prod_wallet',
      name: 'Minimalist Leather Wallet',
      store: 'UrbanEdge Goods',
      price: 34.99,
      img: '/static/img/backpack.jpg',
      qty: 2
    },
    {
      id: 'prod_tracker',
      name: 'Smart Fitness Tracker Band',
      store: 'FitLife Pro',
      price: 54.99,
      img: '/static/img/chair.jpg',
      qty: 1
    }
  ];

  function getCart() {
    try {
      var data = localStorage.getItem(STORAGE_KEY);
      if (!data) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(DEFAULT_ITEMS));
        return DEFAULT_ITEMS.slice();
      }
      var parsed = JSON.parse(data);
      return Array.isArray(parsed) ? parsed : DEFAULT_ITEMS.slice();
    } catch (e) {
      return DEFAULT_ITEMS.slice();
    }
  }

  function saveCart(cart) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(cart));
    } catch (e) {
      console.warn('Unable to save cart to localStorage:', e);
    }
    renderCartUI();
  }

  function addToCart(item) {
    var cart = getCart();
    var existingIndex = -1;
    for (var i = 0; i < cart.length; i++) {
      if (cart[i].id === item.id || cart[i].name === item.name) {
        existingIndex = i;
        break;
      }
    }

    if (existingIndex > -1) {
      cart[existingIndex].qty += (item.qty || 1);
    } else {
      cart.push({
        id: item.id || ('prod_' + Date.now()),
        name: item.name || 'DropHub Product',
        store: item.store || 'DropHub Verified',
        price: parseFloat(item.price) || 29.99,
        img: item.img || '/static/img/headphones.jpg',
        qty: item.qty || 1
      });
    }

    saveCart(cart);
    triggerBadgeBump();
    showToast('Added "' + (item.name || 'Item') + '" to cart!');
  }

  function updateQty(id, delta) {
    var cart = getCart();
    for (var i = 0; i < cart.length; i++) {
      if (cart[i].id === id) {
        cart[i].qty += delta;
        if (cart[i].qty <= 0) {
          cart.splice(i, 1);
        }
        break;
      }
    }
    saveCart(cart);
  }

  function removeItem(id) {
    var cart = getCart();
    var updated = cart.filter(function (item) {
      return item.id !== id;
    });
    saveCart(updated);
  }

  function clearCart() {
    saveCart([]);
  }

  function triggerBadgeBump() {
    var badges = document.querySelectorAll('.cart-badge, .mmenu-cart-count');
    badges.forEach(function (b) {
      b.classList.remove('bump');
      void b.offsetWidth;
      b.classList.add('bump');
    });
  }

  function showToast(message) {
    var toast = document.createElement('div');
    toast.className = 'cart-toast';
    toast.innerHTML =
      '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2.5" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>' +
      '<span>' + message + '</span>';

    document.body.appendChild(toast);
    setTimeout(function () {
      toast.classList.add('cart-toast--fadeout');
      setTimeout(function () {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
      }, 400);
    }, 2800);
  }

  function renderCartUI() {
    var cart = getCart();
    var totalCount = 0;
    var subtotal = 0;

    cart.forEach(function (it) {
      totalCount += it.qty;
      subtotal += (it.price * it.qty);
    });

    /* Update all badge counters across top header and mobile drawer */
    document.querySelectorAll('.cart-badge').forEach(function (el) {
      el.textContent = totalCount;
    });
    document.querySelectorAll('.mmenu-cart-count').forEach(function (el) {
      el.textContent = totalCount;
    });
    document.querySelectorAll('.cart-count-pill').forEach(function (el) {
      el.textContent = totalCount + (totalCount === 1 ? ' ITEM' : ' ITEMS');
    });

    /* Update Subtotal Text */
    document.querySelectorAll('.cart-subtotal strong').forEach(function (el) {
      el.textContent = '$' + subtotal.toFixed(2);
    });

    /* Render Item List inside Cart Dropdown */
    var cartContainers = document.querySelectorAll('.cart-items, #cartItems');
    cartContainers.forEach(function (container) {
      if (!container) return;

      if (cart.length === 0) {
        container.innerHTML =
          '<div class="cart-empty-state">' +
            '<div class="cart-empty-icon">' +
              '<svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.8" stroke-linecap="round"><path d="M6 8h15l-1.2 11a1.5 1.5 0 0 1-1.5 1.3H8.7a1.5 1.5 0 0 1-1.5-1.3L6 8z"/><path d="M9 10V6a3 3 0 0 1 6 0v4"/></svg>' +
            '</div>' +
            '<p class="cart-empty-title">Your cart is empty</p>' +
            '<p class="cart-empty-sub">Explore our curated drops and pay your way with Pi, PayPal & Naira.</p>' +
            '<a href="/shop/" class="cart-empty-btn">Browse Shop →</a>' +
          '</div>';
        return;
      }

      var html = '';
      cart.forEach(function (item) {
        var itemTotal = (item.price * item.qty).toFixed(2);
        html +=
          '<div class="cart-item" data-id="' + item.id + '">' +
            '<div class="cart-thumb"><img src="' + item.img + '" alt="' + item.name + '" /></div>' +
            '<div class="cart-info">' +
              '<p class="cart-name">' + item.name + '</p>' +
              '<p class="cart-store">' + item.store + '</p>' +
              '<div class="cart-row">' +
                '<div class="qty-pill">' +
                  '<button type="button" class="btn-qty-minus" data-id="' + item.id + '" aria-label="Decrease quantity">−</button>' +
                  '<span>' + item.qty + '</span>' +
                  '<button type="button" class="btn-qty-plus" data-id="' + item.id + '" aria-label="Increase quantity">+</button>' +
                '</div>' +
                '<span class="cart-price">$' + itemTotal + '</span>' +
              '</div>' +
            '</div>' +
            '<button type="button" class="cart-trash btn-cart-remove" data-id="' + item.id + '" aria-label="Remove item">✕</button>' +
          '</div>';
      });

      container.innerHTML = html;
    });
  }

  /* Handle global click delegation for cart operations */
  document.addEventListener('click', function (e) {
    /* Quantity Minus */
    var btnMinus = e.target.closest('.btn-qty-minus');
    if (btnMinus) {
      e.preventDefault();
      e.stopPropagation();
      var idMinus = btnMinus.getAttribute('data-id');
      updateQty(idMinus, -1);
      return;
    }

    /* Quantity Plus */
    var btnPlus = e.target.closest('.btn-qty-plus');
    if (btnPlus) {
      e.preventDefault();
      e.stopPropagation();
      var idPlus = btnPlus.getAttribute('data-id');
      updateQty(idPlus, 1);
      return;
    }

    /* Checkout button inside dropdown: fall back to checkout.html if link is a stub */
    var btnCheckout = e.target.closest('.cart-btn-checkout');
    if (btnCheckout) {
      var ckHref = btnCheckout.getAttribute('href');
      if (!ckHref || ckHref === '#') {
        e.preventDefault();
        window.location.href = '/checkout/';
        return;
      }
    }

    /* Remove Item */
    var btnRemove = e.target.closest('.btn-cart-remove');
    if (btnRemove) {
      e.preventDefault();
      e.stopPropagation();
      var idRem = btnRemove.getAttribute('data-id');
      removeItem(idRem);
      return;
    }

    /* Add to Cart button on product cards (.pc-add or .btn-add-cart) */
    var addBtn = e.target.closest('.pc-add, .btn-add-cart');
    if (addBtn) {
      e.preventDefault();
      var card = addBtn.closest('.product-card, .shop-card, [data-name]');
      if (card) {
        var name = card.getAttribute('data-name') || card.querySelector('.pc-name, h3')?.textContent?.trim() || 'DropHub Product';
        var price = card.getAttribute('data-price') || card.querySelector('.pc-price')?.textContent?.replace(/[^0-9.]/g, '') || '49.99';
        var store = card.querySelector('.pc-store')?.textContent?.trim() || 'Verified Store';
        var imgEl = card.querySelector('img');
        var img = imgEl ? imgEl.getAttribute('src') : '/static/img/headphones.jpg';
        var id = card.getAttribute('data-id') || name.toLowerCase().replace(/[^a-z0-9]+/g, '_');

        addToCart({
          id: id,
          name: name,
          price: parseFloat(price),
          store: store,
          img: img,
          qty: 1
        });

        /* Visual feedback on button */
        var origHtml = addBtn.innerHTML;
        addBtn.classList.add('added');
        addBtn.innerHTML = '✓ Added';
        setTimeout(function () {
          addBtn.classList.remove('added');
          addBtn.innerHTML = origHtml;
        }, 1500);
      }
    }
  });

  /* Setup Header Dropdown Toggle Logic */
  function initCartDropdownToggle() {
    var wrap = document.querySelector('.cart-wrap');
    var toggle = document.getElementById('cartToggle');
    var dd = document.getElementById('cartDropdown');
    var close = document.getElementById('cartClose');

    if (!wrap || !toggle || !dd) return;

    function setOpen(open) {
      wrap.classList.toggle('open', open);
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      dd.setAttribute('aria-hidden', open ? 'false' : 'true');
    }

    toggle.addEventListener('click', function (e) {
      e.stopPropagation();
      setOpen(!wrap.classList.contains('open'));
    });

    if (close) {
      close.addEventListener('click', function (e) {
        e.stopPropagation();
        setOpen(false);
      });
    }

    document.addEventListener('click', function (e) {
      if (!wrap.contains(e.target)) {
        setOpen(false);
      }
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') setOpen(false);
    });
  }

  /* Expose Global API for manual calls if needed */
  window.DropHubCart = {
    getCart: getCart,
    addToCart: addToCart,
    updateQty: updateQty,
    removeItem: removeItem,
    clearCart: clearCart,
    render: renderCartUI
  };

  /* Initialize on DOMContentLoaded */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      renderCartUI();
      initCartDropdownToggle();
    });
  } else {
    renderCartUI();
    initCartDropdownToggle();
  }

})();
