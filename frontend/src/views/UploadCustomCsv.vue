<template>
  <vue-csv-import
      url="/api/upload-custom-csv/"
      :autoMatchFields="true"
      :autoMatchIgnoreCase="true"
      :headers="true"
      :canIgnore="true"

      :callback="on_success"
      :catch="on_failure"

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
</template>

<script>

import VueCsvImport from "@/components/VueCsvImport.vue";

export default {
  name: 'UploadCustomCsv',
  components: {VueCsvImport},

  methods: {
    on_success(response, dry, updatePrice, updateInventory) {
      this.$emit("input", response.data.custom_csv_data_id, dry, updatePrice, updateInventory);
    },
    on_failure(axios_error) {
      this.$buefy.toast.open({
        duration: 5000,
        message: axios_error.response.data.error || 'Something went wrong',
        position: 'is-top',
        type: 'is-danger'
      })
    }
  }
}
</script>
