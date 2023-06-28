<template>
  <div class="container">
    <b-tabs type="is-boxed" :animated="false">
      <b-tab-item label="Products sync">
        <b-table :data="products_log_groups" :loading="loading">
          <b-table-column field="id" label="ID" v-slot="props">
            {{ props.row.gid }}
          </b-table-column>

          <b-table-column field="time" label="Time" v-slot="props">
            {{ formatTime(props.row.time) }}
          </b-table-column>

          <b-table-column field="source" label="Source" v-slot="props">
            {{ props.row.source }}
          </b-table-column>

          <b-table-column v-slot="props">
            <b-button @click="downloadLogCsv(props.row, 'products')" label="Download CSV"
                      type="is-secondary" size="is-small" class="is-pulled-right"/>
          </b-table-column>

        </b-table>
      </b-tab-item>
      <b-tab-item label="Orders sync">
        <b-table :data="orders_log_groups" :loading="loading">
          <b-table-column field="id" label="ID" v-slot="props">
            {{ props.row.gid }}
          </b-table-column>

          <b-table-column field="time" label="Time" v-slot="props">
            {{ formatTime(props.row.time) }}
          </b-table-column>

          <b-table-column v-slot="props">
            <b-button @click="downloadLogCsv(props.row, 'orders')" label="Download CSV"
                      type="is-secondary" size="is-small" class="is-pulled-right"/>
          </b-table-column>
        </b-table>
      </b-tab-item>
    </b-tabs>

  </div>

</template>

<script>
import axios from "axios";
import DownloadFileMixin from "@/mixins/DownloadFileMixin.vue";

export default {
  name: "LogsListView",
  mixins: [DownloadFileMixin],

  data() {
    return {
      products_log_groups: [],
      orders_log_groups: [],
      loading: false
    }
  },

  async mounted() {
    this.loading = true
    this.products_log_groups = await this.getLogGroups('products')
    this.orders_log_groups = await this.getLogGroups('orders')
    this.loading = false
  },

  methods: {
    downloadLogCsv(row, type) {
      const url = `/api/${type}_sync_logs/download-csv/${row.gid}`
      this.downloadFile(url)
    },

    formatTime(timeString) {
      // Convert the string to a Date object
      const date = new Date(timeString);

      return date.toLocaleString('default', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })

    },

    async getLogGroups(type) {
      const res = await axios.get(`/api/${type}_sync_logs/groups`);
      return res.data

    }
  }
}
</script>

<style scoped>

</style>