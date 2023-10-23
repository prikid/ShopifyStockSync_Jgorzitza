<template>
  <div>
    <b-loading :is-full-page="true" v-model="isLoading" :can-cancel="false"></b-loading>
  <vue-csv-import
      url="/api/upload-custom-csv/"
      :autoMatchFields="true"
      :autoMatchIgnoreCase="true"
      :headers="true"
      :canIgnore="true"
      :shopify-locations="shopifyLocations"

      @input="before_uploading"
      :callback="on_success"
      :catch="on_failure"
      :finally="on_finally"

      :mandatory-fields="['barcode', 'sku']"

      submitBtnText="Upload & Sync"
      submitBtnClass="button is-primary"

      submitDryBtnText="Upload & Dry run"
      submitDryBtnClass="button is-secondary"

      buttonClass="button ml-2"
      tableClass="table"
      tableSelectClass="select"
  >
  </vue-csv-import>
  </div>

</template>

<script>

import VueCsvImport from "@/components/VueCsvImport.vue";

export default {
  name: 'UploadCustomCsv',
  components: {VueCsvImport},

  props: {
    shopifyLocations: Array
  },

  data: () => ({
    isLoading: false
  }),

  methods: {
    before_uploading() {
      this.isLoading = true;
    },
    on_success(response, dry, updatePrice, updateInventory, shopifyInventoryLocation) {
      this.$emit("input", response.data.custom_csv_id, dry, updatePrice, updateInventory, shopifyInventoryLocation);
    },
    on_failure(axios_error) {
      this.$buefy.toast.open({
        duration: 5000,
        message: axios_error.response.data.error || 'Something went wrong',
        position: 'is-top',
        type: 'is-danger'
      })
    },
    on_finally() {
      this.isLoading = false;
    }
  }
}
</script>
