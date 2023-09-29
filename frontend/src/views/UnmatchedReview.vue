<template>
  <section>
    <b-table
        :data="products_list"
        ref="table"
        :loading="loading"
        paginated
        backend-pagination
        :total="total"
        :per-page="perPage"
        @page-change="onPageChange"


        detailed
        detail-key="shopify_variant_id"
        :show-detail-icon="true"
        :opened-detailed="defaultOpenedDetails"
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
                        :disabled="!new_barcodes[props.row.shopify_variant_id]"
                        @click="replaceBarcodeOnShopify(props.row)"
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
      defaultOpenedDetails: [],
      new_barcodes: {},

      total: 0,
      page: 1,
      perPage: 30
    }
  },

  async mounted() {
    this.loading = true;
    await this.loadData();
    this.defaultOpenedDetails = this.products_list.length ? [this.products_list[0]['shopify_variant_id']] : [];
    this.loading = false;
  },

  methods: {
    onPageChange(page) {
      this.page = page;
      this.loadData();
    },

    async loadData() {
      const params = [
        `page=${this.page}`,
        `per_page=${this.perPage}`
      ].join('&')
      const response = await axios.get(`/api/unmatched_review?${params}`);

      this.total = response.data.count;
      this.products_list = response.data.results;
    },

    async replaceBarcodeOnShopify(row) {
      try {
        const new_barcode = this.new_barcodes[row.shopify_variant_id];
        const response = await axios.put(`/api/unmatched_review/${row.id}/`, {
          new_barcode: new_barcode
        });

        if (response.status === 200) {
          Toast.open({
            message: `The new barcode ${new_barcode} has been set to the product variant ${row.shopify_variant_id}  `,
            type: 'is-success',
            duration: 5000
          });

          await this.loadData();
        }
        else {
          throw new Error(response.statusText);
        }
      } catch (e) {
        console.log(e);
        Toast.open({message: "Something went wrong!", type: 'is-danger'});
      }
    }
  },
}
</script>