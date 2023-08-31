import Vue from 'vue'
import VueRouter from 'vue-router'
import HomeView from '../views/HomeView.vue'
import store from "../store";
import LoginView from "../views/LoginView.vue";
import NotFound from "@/views/NotFound.vue";
import LogsListView from "@/views/LogsListView.vue";
import UploadCustomCSV from "@/views/UploadCustomCsv.vue";
import UnmatchedReview from "@/views/UnmatchedReview.vue";

Vue.use(VueRouter)

const routes = [
    {
        path: '/',
        name: 'home',
        component: HomeView
    },
    {
        path: '/login',
        name: 'login',
        component: LoginView
    },
    {
        path: '/dashboard',
        name: 'dashboard',
        meta: {
            requireLogin: true
        },

        // route level code-splitting
        // this generates a separate chunk (about.[hash].js) for this route
        // which is lazy-loaded when the route is visited.
        component: () => import(/* webpackChunkName: "dashboard" */ '../views/Dashboard.vue')
    },
    {
        path: '/logs',
        name: 'logs',
        meta: {
            requireLogin: true
        },
        component: LogsListView
    },
    {
        path: '/unmatched_review',
        name: 'unmatched_review',
        meta: {
            requireLogin: true
        },
        component: UnmatchedReview
    },
    {
        path: '/upload-custom-csv',
        name: 'uploadCustomCSV',
        component: UploadCustomCSV
    },
    {
        path: "/:notFound",
        component: NotFound,
    },

]

const router = new VueRouter({
    mode: 'history',
    base: process.env.BASE_URL,
    routes
})

router.beforeEach((to, from, next) => {
    if (to.matched.some(record => record.meta.requireLogin) && !store.getters.isAuthenticated) {
        next({name: 'login', query: {to: to.path}})
    } else {
        next()
    }
})


export default router
