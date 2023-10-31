<template>
  <div class="column is-4 is-offset-4">
    <login-form
        @authenticated="on_authenticated"
        @authentication_error="on_authentication_error"
    />
  </div>

</template>

<script>
import LoginForm from "@/components/LoginForm.vue";
import showToastsMixin from "@/mixins/ShowToastsMixin.vue";

export default {
  name: 'LoginView',
  mixins:[showToastsMixin],

  components: {
    LoginForm
  },

  methods: {
    on_authenticated() {
      const toPath = this.$route.query.to || '/dashboard';
      this.$router.push(toPath);
    },

    on_authentication_error(e) {
      this.showErrorToast(e,e.message);
    }
  }
}

</script>