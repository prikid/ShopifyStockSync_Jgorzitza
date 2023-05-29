import Vue from 'vue'
import Vuex from 'vuex'
import axios from 'axios'

Vue.use(Vuex)

export default new Vuex.Store({
    state: {
        token: ''
    },
    getters: {
        isAuthenticated: state => Boolean(state.token)
    },
    mutations: {
        setToken(state, token) {
            state.token = token;
            localStorage.setItem('token', token);
            axios.defaults.headers.common['Authorization'] = "Token " + token
        },
        removeToken(state) {
            state.token = '';
            localStorage.setItem('token', '');
            axios.defaults.headers.common['Authorization'] = ''
        }
    },
    actions: {
        initialize(context) {
            const token = localStorage.getItem('token')
            if (token)
                context.commit('setToken', token);
        }
    },
    modules: {}
})
