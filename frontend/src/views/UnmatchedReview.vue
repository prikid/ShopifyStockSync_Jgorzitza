<template>
  <section>
    <div class="level">
      <div class="level-left">
        <div class="level-item">
          <b-button @click="collapseAll" icon-left="compress" label="Collapse all"/>
          <b-button @click="expandAll" icon-left="expand" label="Expand all"/>
          <b-button @click="selectAll" icon-left="check-circle" title="Select all the first ones" label="Select all"/>
          <b-button @click="clearAll" icon-left="times" label="Clear all"/>
          <b-button type="is-danger" @click="saveAll" icon-left="save" label="Save all"
                    :disabled="!Object.keys(new_barcodes).length"/>
        </div>
      </div>
      <div class="level-right">
        <div class="level-item">
          <b-field>
            <b-checkbox v-model="show_hidden" @input="loadData">Show removed</b-checkbox>
          </b-field>
        </div>
        <div class="level-item">
          <b-field label="Per page">
            <b-select v-model="perPage" @input="onPageChange(1)">
              <option v-for="v in [50,100,200,500,1000]" :value="v" :key="v" v-text="v"/>
            </b-select>
          </b-field>
        </div>
      </div>
    </div>


    <b-table
        :data="products_list"
        ref="table"
        :loading="loading"
        paginated
        backend-pagination
        :total="total"
        :per-page="perPage"
        @page-change="onPageChange"

        striped
        :row-class="row => row.is_hidden ? 'hidden_row':''"
        :has-detailed-visible="row => !row.is_hidden"

        detailed
        detail-key="id"
        :opened-detailed=openedDetailedRows
        :show-detail-icon="true"
        aria-next-label="Next page"
        aria-previous-label="Previous page"
        aria-page-label="Page"
        aria-current-label="Current page"
    >

      <b-table-column field="shopify_variant_id" label="Variant ID" width="40" numeric v-slot="props">
        <a :href="props.row.variant_url" target="_blank" v-text="props.row.shopify_variant_id"/>
      </b-table-column>

      <b-table-column field="shopify_product_id" label="Product ID" width="40" numeric v-slot="props">
        <a :href="props.row.product_url" target="_blank" v-text="props.row.shopify_product_id"/>
      </b-table-column>

      <b-table-column field="shopify_product_title" label="Product title" v-slot="props">
        <a :href="props.row.product_url" target="_blank" v-text="props.row.shopify_product_title"/>
      </b-table-column>

      <b-table-column field="shopify_sku" label="SKU" sortable v-slot="props">
        {{ props.row.shopify_sku }}
      </b-table-column>

      <b-table-column field="shopify_barcode" label="Barcode" v-slot="props">
        {{ props.row.shopify_barcode }}
      </b-table-column>

      <b-table-column field="shopify_variant_title" label="Variant title" v-slot="props">
        {{ props.row.shopify_variant_title }}
      </b-table-column>

      <b-table-column v-slot="props">
        <b-button v-if="props.row.is_hidden" icon-left="trash-restore" @click="removeFromHidden(props.row)" title="Restore item"/>
        <b-button v-else icon-left="trash" @click="addToHidden(props.row)" title="Hide row from the list"/>
      </b-table-column>

      <template #detail="props">
        <!--        {{ props.row.possible_fuse5_products }}-->
        <div class="ml-6">
          <h4 class="has-text-weight-semibold is-italic mb-3">Fuse5 products with a similar SKU:</h4>
          <table>
            <thead>
            <tr>
              <th></th>
              <th>ID</th>
              <th>SKU</th>
              <th>Barcode</th>
              <th>Line code</th>
              <th>Product name</th>
            </tr>
            </thead>
            <tbody>
            <tr v-for="item in props.row.possible_fuse5_products" :key="item.id">
              <td>
                <b-radio v-model="new_barcodes[props.row.shopify_variant_id]"
                         :name="'selected_barcode_' + props.row.shopify_variant_id"
                         :native-value="item.barcode"
                />
              </td>
              <td>{{ item.id }}</td>
              <td>{{ item.sku }}</td>
              <td>{{ item.barcode }}</td>
              <td>{{ item.line_code }}</td>
              <td>{{ item.product_name }}</td>
            </tr>
            </tbody>
          </table>
          <b-field
              :message="'Replace the barcode ' + props.row.shopify_barcode + ' by this one on Shopify?'"
              class="ml-3 mt-3"
          >
            <b-input placeholder="New barcode" v-model="new_barcodes[props.row.shopify_variant_id]"></b-input>
            <p class="control">
              <b-button type="is-danger is-outlined"
                        label="Save to Shopify"
                        icon-left="save"
                        :disabled="!new_barcodes[props.row.shopify_variant_id]"
                        @click="onSaveToShopifyClick(props.row)"
              />
            </p>
          </b-field>
        </div>
      </template>
    </b-table>

  </section>
</template>

<script>
import axios from "axios";
import {ToastProgrammatic as Toast} from 'buefy'

export default {
  name: 'UnmatchedReview',

  data() {
    return {
      products_list: [],
      loading: false,
      openedDetailedRows: [],
      new_barcodes: {},

      show_hidden: false,

      total: 0,
      page: 1,
      perPage: 50
    }
  },

  async mounted() {
    this.loading = true;
    await this.loadData();
    // this.defaultOpenedDetails = this.products_list.length ? [this.products_list[0]['shopify_variant_id']] : [];
    this.loading = false;
  },

  methods: {
    collapseAll() {
      this.openedDetailedRows = [];
    },

    expandAll() {
      this.openedDetailedRows = this.products_list.map((p) => p.id);
    },

    selectAll() {
      this.new_barcodes = this.products_list.reduce((result, product) => {
        const barcodeItem = product.possible_fuse5_products.find(
            (item) => item.barcode !== null && item.barcode !== ""
        );

        if (barcodeItem) {
          result[product.shopify_variant_id] = barcodeItem.barcode;
        }

        return result;
      }, {});
    },

    clearAll() {
      this.new_barcodes = {};
    },

    onPageChange(page) {
      this.page = page;
      this.loadData();
    },

    async loadData() {
      const params = [
        `page=${this.page}`,
        `per_page=${this.perPage}`,
        `show_hidden=${this.show_hidden}`
      ].join('&')

      console.log(params);

      const response = await axios.get(`/api/unmatched_review?${params}`);

      this.total = response.data.count;
      this.products_list = response.data.results;
    },

    async saveAll() {
      const promises = this.products_list.map(async (p) => {
        if (p.shopify_variant_id in this.new_barcodes) {
          await this.replaceBarcodeOnShopify(p);
        }
      });

      // Wait for all replaceBarcodeOnShopify calls to finish
      await Promise.all(promises);

      // Once all promises are resolved, loadData is called
      await this.loadData();
    },

    async onSaveToShopifyClick(row) {
      await this.replaceBarcodeOnShopify(row);
      await this.loadData();
    },

    async replaceBarcodeOnShopify(product) {
      try {
        const new_barcode = this.new_barcodes[product.shopify_variant_id];
        const response = await axios.put(`/api/unmatched_review/${product.id}/`, {
          new_barcode: new_barcode
        });

        if (response.status === 200) {
          Toast.open({
            message: `The new barcode ${new_barcode} has been set to the product variant ${product.shopify_variant_id}  `,
            type: 'is-success',
            duration: 5000,
            queue: false
          });

        } else {
          throw new Error(response.statusText);
        }
      } catch (e) {
        this.showError(e)
      }
    },

    async addToHidden(row) {
      try {
        const response = await axios.post(`/api/unmatched_hidden/`, {
          shopify_product_id: row.shopify_product_id,
          shopify_variant_id: row.shopify_variant_id
        });

        if (response.status === 201)
          this.loadData();
        else
          throw new Error(response.statusText);

      } catch (e) {
        this.showError(e);
      }
    },

    async removeFromHidden(row) {
      try {
        const response = await axios.post(`/api/unmatched_hidden/destroy_by_product_ids/`, {
          shopify_product_id: row.shopify_product_id,
          shopify_variant_id: row.shopify_variant_id
        });

        if (response.status === 204)
          this.loadData();
        else
          throw new Error(response.statusText);

      } catch (e) {
        this.showError(e);
      }
    },

    showError(e) {
      console.log(e);
      const error_msg = e.response?.data?.error ?? "Something went wrong";
      Toast.open({message: error_msg, type: 'is-danger', queue: false, duration: 5000});
    }
  },
}
</script>

<style>
tr.hidden_row {
  background: #9b9b9b!important;
}
</style>