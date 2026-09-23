import { CategorySelector } from "@point_of_sale/app/components/category_selector/category_selector";
import { patch } from "@web/core/utils/patch";
import { useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";

CategorySelector.template = "wu_pos_categories.CategorySelector";

patch(CategorySelector.prototype, {
    setup() {
        super.setup(...arguments);
        this.scrollTrackRef = useRef("categoryScrollTrack");

        this.state = useState({
            canScrollLeft: false,
            canScrollRight: false,
            isOverflowOpen: false,
        });

        this.isDragging = false;
        this.startX = 0;
        this.scrollStartLeft = 0;

        this.onWindowClick = (ev) => {
            if (this.state && this.state.isOverflowOpen) {
                this.state.isOverflowOpen = false;
            }
        };

        this.onResize = () => {
            this.updateScrollButtons();
        };

        this.onTrackScroll = this.onTrackScroll.bind(this);
        this.onTrackWheel = this.onTrackWheel.bind(this);
        this.onMouseDown = this.onMouseDown.bind(this);
        this.onMouseMove = this.onMouseMove.bind(this);
        this.onMouseUp = this.onMouseUp.bind(this);
        this.toggleOverflow = this.toggleOverflow.bind(this);

        onMounted(() => {
            window.addEventListener("click", this.onWindowClick);
            window.addEventListener("resize", this.onResize);
            setTimeout(() => {
                this.updateScrollButtons();
                this.scrollToSelectedCategory();
            }, 50);
        });

        onWillUnmount(() => {
            window.removeEventListener("click", this.onWindowClick);
            window.removeEventListener("resize", this.onResize);
        });
    },

    updateScrollButtons() {
        const el = this.scrollTrackRef?.el;
        if (!el) {
            return;
        }
        const hasOverflow = el.scrollWidth > el.clientWidth + 2;
        const canLeft = el.scrollLeft > 2;
        const canRight = hasOverflow && (el.scrollLeft < el.scrollWidth - el.clientWidth - 2);

        if (this.state && this.state.canScrollLeft !== canLeft) {
            this.state.canScrollLeft = canLeft;
        }
        if (this.state && this.state.canScrollRight !== canRight) {
            this.state.canScrollRight = canRight;
        }
    },

    onTrackScroll() {
        this.updateScrollButtons();
    },

    onTrackWheel(ev) {
        const el = this.scrollTrackRef?.el;
        if (el && ev.deltaY) {
            ev.preventDefault();
            el.scrollLeft += ev.deltaY;
            this.updateScrollButtons();
        }
    },

    scrollCarousel(direction) {
        const el = this.scrollTrackRef?.el;
        if (!el) {
            return;
        }
        const scrollAmount = Math.max(el.clientWidth * 0.6, 200);
        if (direction === "left") {
            el.scrollBy({ left: -scrollAmount, behavior: "smooth" });
        } else {
            el.scrollBy({ left: scrollAmount, behavior: "smooth" });
        }
        setTimeout(() => this.updateScrollButtons(), 350);
    },

    onMouseDown(ev) {
        if (ev.button !== 0) return;
        const el = this.scrollTrackRef?.el;
        if (!el) return;
        this.isDragging = true;
        this.startX = ev.pageX - el.offsetLeft;
        this.scrollStartLeft = el.scrollLeft;
    },

    onMouseMove(ev) {
        if (!this.isDragging) return;
        ev.preventDefault();
        const el = this.scrollTrackRef?.el;
        if (!el) return;
        const x = ev.pageX - el.offsetLeft;
        const walk = (x - this.startX) * 1.5;
        el.scrollLeft = this.scrollStartLeft - walk;
        this.updateScrollButtons();
    },

    onMouseUp() {
        this.isDragging = false;
    },

    toggleOverflow(ev) {
        ev?.stopPropagation();
        if (this.state) {
            this.state.isOverflowOpen = !this.state.isOverflowOpen;
        }
    },

    selectCategory(categoryId) {
        this.pos.setSelectedCategory(categoryId);
        if (this.state) {
            this.state.isOverflowOpen = false;
        }
        setTimeout(() => {
            this.scrollToSelectedCategory();
            this.updateScrollButtons();
        }, 100);
    },

    scrollToSelectedCategory() {
        const el = this.scrollTrackRef?.el;
        if (!el) return;
        const selectedId = this.pos?.selectedCategory?.id;
        if (!selectedId) return;
        const btn = el.querySelector(`[data-category-id="${selectedId}"]`);
        if (btn && typeof btn.scrollIntoView === "function") {
            btn.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
        }
    },

    getCategoryColorIndex(category) {
        if (category?.color && category.color > 0) {
            return category.color;
        }
        const id = category?.id || 1;
        return (id % 12) + 1;
    },

    getCategoryClass(category) {
        const colorIdx = this.getCategoryColorIndex(category);
        const isSelected = Boolean(category?.isSelected);
        const isChild = Boolean(category?.isChildren);

        let colorClass = `wu_pos_categ_color_${colorIdx}`;
        if (category?.color) {
            colorClass = `o_colorlist_item_color_${category.color}`;
        }

        return {
            [colorClass]: true,
            'is-selected': isSelected,
            'is-child': isChild,
            'opacity-75 border-0': !isChild && !isSelected,
            'fw-bold': isSelected,
            'shadow-sm': isSelected,
        };
    },

    getCategoryColorDotClass(category) {
        const colorIdx = this.getCategoryColorIndex(category);
        if (category?.color) {
            return `o_colorlist_item_color_${category.color}`;
        }
        return `wu_pos_categ_color_${colorIdx}`;
    }
});
